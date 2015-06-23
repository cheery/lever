from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rtyper.lltypesystem import rffi, lltype
import bincode.common
import bincode.decoder
import optable
import space

u16_array = lltype.GcArray(rffi.USHORT)

def from_file(path):
    stream = bincode.decoder.open_file(path)
    assert stream.read(8) == bincode.common.header
    functions = []
    for i in range(stream.read_u16()):
        flags = stream.read_u16()
        regc = stream.read_u16()
        argc = stream.read_u16()
        localc = stream.read_u16()
        blocklen = stream.read_u16()
        block = lltype.malloc(u16_array, blocklen)
        for i in range(blocklen):
            block[i] = rffi.r_ushort(stream.read_u16())
        functions.append(Function(flags, regc, argc, localc, block))
    constants = []
    for i in range(stream.read_u16()):
        klass = stream.read_ubyte()
        if klass == 1:
            constants.append(space.String(stream.read_string()))
        elif klass == 2:
            constants.append(space.Integer(rffi.r_long(stream.read_u64())))
        elif klass == 3:
            constants.append(space.Integer(-rffi.r_long(stream.read_u64())))
        elif klass == 4:
            constants.append(space.Float(stream.read_double()))
        else:
            assert False, klass
    return Program(Unit(constants[:], functions[:]))

class Closure(space.Object):
    _immutable_fields_ = ['parent', 'function']
    def __init__(self, frame, function):
        self.frame = frame
        self.function = function

    def call(self, argv):
        argc = self.function.argc
        if len(argv) < argc:
            raise space.Error(u"closure requires %d arguments" % argc)
        frame = Frame(self.function, self.frame.module, self.frame)
        for i in range(argc):
            frame.local[i] = argv[i]
        regv = new_register_array(self.function.regc)
        return interpret(0, self.function.block, regv, frame)

class Program(space.Object):
    _immutable_fields_ = ['unit']
    def __init__(self, unit):
        self.unit = unit

    def call(self, argv):
        if len(argv) != 1:
            raise space.Error(u"program expects module as an argument")
        module = argv[0]
        assert isinstance(module, space.Module)
        entry = self.unit.functions[0]
        frame = Frame(entry, module, None)
        regv = new_register_array(entry.regc)
        return interpret(0, entry.block, regv, frame)

class Unit:
    _immutable_fields_ = ['constants[*]', 'functions[*]']
    def __init__(self, constants, functions):
        self.constants = constants
        self.functions = functions
        for function in functions:
            function.unit = self

class Function:
    _immutable_fields_ = ['flags', 'regc', 'argc', 'localc', 'block[*]', 'unit']
    def __init__(self, flags, regc, argc, localc, block):
        self.flags = flags
        self.regc = regc
        self.argc = argc
        self.localc = localc
        self.block = block
        self.unit = None

class Frame:
    _immutable_fields_ = ['local', 'module', 'parent', 'unit']
    def __init__(self, function, module, parent):
        self.unit = function.unit
        self.local = [space.null for i in range(function.localc)]
        self.module = module
        self.parent = parent

class RegisterArray:
    _virtualizable_ = ['regs[*]']
    def __init__(self, regs):
        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self.regs = regs

    @always_inline
    def store(self, index, value):
        self.regs[index] = value
    
    @always_inline
    def load(self, index):
        return self.regs[index]

def new_register_array(regc):
    regs = []
    for i in range(regc):
        regs.append(space.null)
    return RegisterArray(regs)

def get_printable_location(pc, block, module, unit):
    return "pc=%d module=%s" % (pc, module.repr().encode('utf-8'))

jitdriver = jit.JitDriver(
    greens=['pc', 'block', 'module', 'unit'], # 'loop_break'
    reds=['regv', 'frame'],
    virtualizables = ['regv'],
    get_printable_location=get_printable_location)

def interpret(pc, block, regv, frame):
    module = jit.promote(frame.module)
    unit   = jit.promote(frame.unit)
    while pc < len(block):
        jitdriver.jit_merge_point(
            pc=pc, block=block, module=module, unit=unit,
            regv=regv, frame=frame)
        opcode = rffi.r_ulong(block[pc])>>8
        ix = pc+1
        pc = ix+rffi.r_ulong(block[pc])&255
        if opcode == opcode_of('assert'):
            if space.is_false(regv.load(block[ix+0])):
                raise space.Error(u"Assertion error")
        elif opcode == opcode_of('constant'):
            regv.store(block[ix+0], unit.constants[block[ix+1]])
        elif opcode == opcode_of('list'):
            contents = []
            for i in range(ix+1, pc):
                contents.append(regv.load(block[i]))
            regv.store(block[ix], space.List(contents))
        elif opcode == opcode_of('move'):
            regv.store(block[ix+0], regv.load(block[ix+1]))
        elif opcode == opcode_of('call'):
            op_call(regv, block, ix, pc)
        elif opcode == opcode_of('return'):
            return regv.load(block[ix+0])
        elif opcode == opcode_of('jump'):
            pc = rffi.r_ulong(block[ix+0])
        elif opcode == opcode_of('cond'):
            if space.is_false(regv.load(block[ix+0])):
                pc = rffi.r_ulong(block[ix+2])
            else:
                pc = rffi.r_ulong(block[ix+1])
        elif opcode == opcode_of('func'):
            regv.store(block[ix+0],
                Closure(frame, unit.functions[block[ix+1]]))
        # these are missing.
        #elif isinstance(op, Next):
        #    regv.store(op.i, regv.load(op.it.i).callattr(u'next', []))
        #elif isinstance(op, Yield):
        #    raise YieldIteration(op.block, loop_break, op.i, regv.load(op.value.i))
        #elif isinstance(op, SetBreak):
        #    loop_break = op.block
        #elif isinstance(op, Iter):
        #    regv.store(op.i, regv.load(op.value.i).iter())

        elif opcode == opcode_of('getattr'):
            name = get_string(unit, block, ix+2)
            obj = regv.load(block[ix+1])
            regv.store(block[ix+0], obj.getattr(name))
        elif opcode == opcode_of('setattr'):
            value = regv.load(block[ix+3])
            name = get_string(unit, block, ix+2)
            obj = regv.load(block[ix+1])
            regv.store(block[ix+0], obj.setattr(name, value))
        elif opcode == opcode_of('getitem'):
            index = regv.load(block[ix+2])
            obj = regv.load(block[ix+1])
            regv.store(block[ix+0], obj.getitem(index))
        elif opcode == opcode_of('setitem'):
            item = regv.load(block[ix+3])
            index = regv.load(block[ix+2])
            obj = regv.load(block[ix+1])
            regv.store(block[ix+0], obj.setitem(index, item))
        elif opcode == opcode_of('getloc'):
            regv.store(block[ix+0], frame.local[block[ix+1]])
        elif opcode == opcode_of('setloc'):
            value = regv.load(block[ix+2])
            frame.local[block[ix+1]] = value
            regv.store(block[ix+0], value)
        elif opcode == opcode_of('getupv'):
            value = get_upframe(frame, block[ix+1]).local[block[ix+2]]
            regv.store(block[ix+0], value)
        elif opcode == opcode_of('setupv'):
            value = regv.load(block[ix+3])
            get_upframe(frame, block[ix+1]).local[block[ix+2]] = value
            regv.store(block[ix+0], value)
        elif opcode == opcode_of('getglob'):
            regv.store(block[ix+0],
                module.getattr(get_string(unit, block, ix+1)))
        elif opcode == opcode_of('setglob'):
            regv.store(block[ix+0],
                module.setattr(
                    get_string(unit, block, ix+1),
                    regv.load(block[ix+2])))
        else:
            raise space.Error(u"unexpected instruction: " + optable.names.get(opcode, str(opcode)).decode('utf-8'))
    return space.null

@jit.unroll_safe
def op_call(regv, block, ix, pc):
    callee = regv.load(block[ix+1])
    argv = []
    for i in range(ix+2, pc):
        argv.append(regv.load(block[i]))
    regv.store(block[ix], callee.call(argv))

@jit.unroll_safe
def get_upframe(frame, index):
    parent = frame.parent
    for i in range(index):
        parent = parent.parent
    return parent

@specialize.memo()
def opcode_of(opname):
    return optable.enc[opname][0]

@always_inline
def get_string(unit, block, i):
    obj = unit.constants[block[i]]
    assert isinstance(obj, space.String)
    return obj.string
