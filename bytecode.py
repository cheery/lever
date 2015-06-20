from instruction_format import dec_code, opcode, opname, ARG_LOCAL, ARG_RAW, ARG_CONST, ARG_BLOCK, ARG_SHIFT
from rpython.rlib import jit
from rpython.rlib.objectmodel import always_inline, specialize
from space import *
import bincode.common
import bincode.decoder
import space
import sys

class ActivationRecord:
    _immutable_fields_ = ['body', 'local', 'module', 'parent']
    def __init__(self, body, module, parent):
        self.body = body
        self.local = [space.null for i in range(body.localc)]
        self.module = module
        self.parent = parent

class Body:
    _immutable_fields_ = ['consttab[*]', 'flags', 'tmpc', 'argc', 'localc', 'blocks[*]', 'functions[*]']
    def __init__(self, flags, tmpc, argc, localc, blocks, functions):
        self.consttab = None
        self.flags = flags
        self.tmpc = tmpc
        self.argc = argc
        self.localc = localc
        self.blocks = blocks
        self.functions = functions

    def set_consttab(self, consttab):
        self.consttab = consttab
        for function in self.functions:
            function.set_consttab(consttab)

    def debug_print(self, indent=''):
        print indent + 'flags', hex(self.flags)
        print indent + 'argc', self.argc
        print indent + 'localc', self.localc
        for i, block in enumerate(self.blocks):
            print indent + 'block', i
            pc = 0
            while pc < len(block):
                pc, opcode, args = dec_code(block, pc)
                print indent + " ", opname(opcode), args
        for i, func in enumerate(self.functions):
            print indent + 'function', i
            func.debug_print(indent + '  ')

class Closure(space.Object):
    _immutable_fields_ = ['frame', 'body']
    def __init__(self, frame, body):
        self.frame = frame
        self.body = body

    def call(self, argv):
        argc = self.body.argc
        if len(argv) < argc:
            raise space.Error(u"closure requires %d arguments" % argc)
        frame = ActivationRecord(self.body, self.frame.module, self.frame)
        for i in range(argc):
            frame.local[i] = argv[i]
        return interpret(frame)

class Frame:
    _virtualizable_ = ['tmp[*]'] # XXX
    def __init__(self, tmp):
        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self.tmp = tmp

    @always_inline
    def store(self, index, value):
        assert index >= 0
        self.tmp[index] = value
    
    @always_inline
    def load(self, index):
        assert index >= 0
        return self.tmp[index]

class Program(space.Object):
    _immutable_fields_ = ['body']
    def __init__(self, body):
        self.body = body

    def call(self, argv):
        if len(argv) != 1:
            raise space.Error(u"program expects module as an argument")
        module = argv[0]
        assert isinstance(module, Module)
        frame = ActivationRecord(self.body, module, None)
        return interpret(frame)

def interpret(frame):
    block = frame.body.blocks[0]
    tmp = []
    for i in range(frame.body.tmpc):
        tmp.append(space.null)
    tmp = Frame(tmp)
    return interpret_body(block, tmp, frame)

def get_printable_location(pc, block, cl_frame_module):
    #if loop_break is None:
    return "pc=%d module=%s" % (pc, cl_frame_module.repr().encode('utf-8'))
    #return "pc=%d block=%d loop_break=%d module=%s" % (pc, body.blocks.index(block), loop_break.index, cl_frame_module.repr().encode('utf-8'))

jitdriver = jit.JitDriver(
    greens=['pc', 'block', 'module'], # 'loop_break'
    reds=['cl_frame', 'frame'],
    virtualizables = ['frame'], # XXX
    get_printable_location=get_printable_location)
def interpret_body(block, frame, cl_frame):#, loop_break):
    pc = 0
    module = jit.promote(cl_frame.module)
    while pc < len(block):
        jitdriver.jit_merge_point(
            pc=pc, block=block, module=module, #loop_break=loop_break, module=module,
            cl_frame=cl_frame, frame=frame)
        pc, op, args = dec_code(block, pc)
        print "pc = %d" % pc
        if False:
            pass
        elif op == opcode('asrt') and len(args) == 1:
            if space.is_false(frame.load(local_arg(args, 0))):
                raise space.Error(u"Assertion error")
        elif op == opcode('cnst') and len(args) == 2:
            frame.store(local_arg(args, 0), const_arg(cl_frame, args, 1))
        elif op == opcode('call') and len(args) > 1:
            do_call(frame, args)
        elif op == opcode('cond') and len(args) == 3:
            pc = 0
            if space.is_false(frame.load(local_arg(args, 0))):
                block = block_arg(cl_frame, args, 2)
            else:
                block = block_arg(cl_frame, args, 1)
        elif op == opcode('jump') and len(args) == 1:
            pc = 0
            block = block_arg(cl_frame, args, 0)
        elif op == opcode('move') and len(args) == 2:
            frame.store(local_arg(args, 0), frame.load(local_arg(args, 1)))
        elif op == opcode('func') and len(args) == 2:
            frame.store(local_arg(args, 0),
                    Closure(cl_frame, cl_frame.body.functions[raw_arg(args, 1)]))
        elif op == opcode('list'):
            contents = []
            for i in range(1, len(args)):
                contents.append(frame.load(local_arg(args, i)))
            frame.store(local_arg(args, 0), space.List(contents))

        # these are missing.
        #elif isinstance(op, Next):
        #    frame.store(op.i, frame.load(op.it.i).callattr(u'next', []))
        #elif isinstance(op, Yield):
        #    raise YieldIteration(op.block, loop_break, op.i, frame.load(op.value.i))
        #elif isinstance(op, SetBreak):
        #    loop_break = op.block
        #elif isinstance(op, Iter):
        #    frame.store(op.i, frame.load(op.value.i).iter())

        elif op == opcode('gatr') and len(args) == 3:
            name = const_arg(cl_frame, args, 2)
            assert isinstance(name, space.String)
            frame.store(local_arg(args, 0),
                frame.load(local_arg(args, 1)).getattr(name.string))
        elif op == opcode('satr') and len(args) == 4:
            name = const_arg(cl_frame, args, 2)
            assert isinstance(name, space.String)
            frame.store(local_arg(args, 0),
                frame.load(local_arg(args, 1))
                .setattr(name.string,
                    frame.load(local_arg(args, 3))))
        elif op == opcode('gitm') and len(args) == 3:
            frame.store(local_arg(args, 0),
                frame.load(local_arg(args, 1))
                .getitem(frame.load(local_arg(args, 2))))
        elif op == opcode('sitm') and len(args) == 4:
            frame.store(local_arg(args, 0),
                frame.load(local_arg(args, 1))
                .setitem(
                    frame.load(local_arg(args, 2)),
                    frame.load(local_arg(args, 3))))
        elif op ==  opcode('gloc') and len(args) == 2:
            frame.store(local_arg(args, 0),
                cl_frame.local[raw_arg(args, 1)])
        elif op ==  opcode('sloc') and len(args) == 3:
            value = frame.load(local_arg(args, 2))
            cl_frame.local[raw_arg(args, 1)] = value
            frame.store(local_arg(args, 0), value)
        elif op == opcode('gup') and len(args) == 3:
            parent = cl_frame.parent
            for i in range(raw_arg(args, 1)):
                parent = parent.parent
            frame.store(local_arg(args, 0), cl_frame.local[raw_arg(args, 2)])
        elif op ==  opcode('sup') and len(args) == 4:
            parent = cl_frame.parent
            for i in range(raw_arg(args, 1)):
                parent = parent.parent
            value = frame.load(local_arg(args, 3))
            parent.local[raw_arg(args, 2)] = value
            frame.store(local_arg(args, 0), value)
        elif op == opcode('ret') and len(args) == 1:
            return frame.load(local_arg(args, 0))
        else:
            raise space.Error(u"unexpected instruction: " +
                opname(op).decode('utf-8'))
    return space.null

#            except StopIteration as stopiter:
#                if loop_break is not None:
#                    block = loop_break
#                    loop_break = None
#                    continue
#                op = block[pc-1]
#                error = space.Error(u"stop iteration")
#                error.stacktrace.append((cl_frame, op.start, op.stop))
#                raise error
#        raise space.Error(u"crappy compiler")
#    except space.Error as e:
#        op = block[pc-1]
#        e.stacktrace.append((cl_frame, op.start, op.stop))
#        raise e

@always_inline
def local_arg(args, index):
    return arg_as(args, index, ARG_LOCAL)

@always_inline
def raw_arg(args, index):
    return arg_as(args, index, ARG_RAW)

@always_inline
def block_arg(cl_frame, args, index):
    return cl_frame.body.blocks[arg_as(args, index, ARG_BLOCK)]

@always_inline
def const_arg(cl_frame, args, index):
    return cl_frame.body.consttab[arg_as(args, index, ARG_CONST)]

ARG_MASK = ((1 << ARG_SHIFT) - 1)
@always_inline
def arg_as(args, index, flag):
    val = args[index]
    if not val & ARG_MASK:
        raise space.Error(u"instruction format violation") 
    return args[index] >> ARG_SHIFT


@jit.unroll_safe
def do_call(frame, args):
    index = local_arg(args, 0)
    callee = frame.load(local_arg(args, 1))
    argv = []
    for i in range(2, len(args)):
        argv.append(frame.load(local_arg(args, i)))
    frame.store(index, callee.call(argv))

def from_file(path):
    stream = bincode.decoder.open_file(path)
    assert stream.read(8) == bincode.common.header
    function = read_function(stream)
    consttab = []
    count = stream.read_integer()
    for i in range(count):
        klass = stream.read_ubyte()
        if klass == 1:
            consttab.append(String(stream.read_string()))
        elif klass == 2:
            consttab.append(Integer(stream.read_i64()))
        elif klass == 3:
            consttab.append(Float(stream.read_double()))
        else:
            assert False, klass
    function.set_consttab(consttab[:])
    return Program(function)

def main():
    for arg in sys.argv[1:]:
        stream = bincode.decoder.open_file(arg)
        assert stream.read(8) == bincode.common.header
        consttab = []
        function = read_function(stream)
        count = stream.read_integer()
        for i in range(count):
            klass = stream.read_ubyte()
            if klass == 1:
                consttab.append(String(stream.read_string()))
            elif klass == 2:
                consttab.append(Integer(stream.read_i64()))
            elif klass == 3:
                consttab.append(Float(stream.read_double()))
            else:
                assert False, klass
        function.debug_print()

def read_function(stream):
    flags = stream.read_integer()
    tmpc = stream.read_integer()
    argc = stream.read_integer()
    localc = stream.read_integer()
    blockc = stream.read_integer()
    blocks = []
    for i in range(blockc):
        length = stream.read_integer()
        blocks.append(stream.read(length))
    functions = []
    functionc = stream.read_integer()
    for i in range(functionc):
        functions.append(read_function(stream))
    return Body(flags, tmpc, argc, localc, blocks, functions)

if __name__=='__main__': main()
