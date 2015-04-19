from rpython.rlib.objectmodel import always_inline
from rpython.rlib import jit
import base
import reader
import space

class ProgramBody:
    def __init__(self, blocks, functions, is_generator):
        self.blocks = blocks
        self.functions = functions
        self.is_generator = is_generator
        self.tmpc = 0
        for block in blocks:
            block.freeze()
            for op in block:
                if isinstance(op, ValuedOp):
                    op.i = self.tmpc
                    self.tmpc += 1

class ActivationRecord:
    _immutable_fields_ = ['module', 'parent']
    def __init__(self, module, parent):
        self.var = {}
        self.module = module
        self.parent = parent

class Program(space.Object):
    _immutable_fields_ = ['body']
    def __init__(self, body):
        self.body = body

    def call(self, argv):
        if len(argv) != 1:
            raise space.Error(u"program expects module as an argument")
        module = argv[0]
        assert isinstance(module, space.Module)
        frame = ActivationRecord(module, None)
        return interpret(self.body, frame)

class Closure(space.Object):
    _immutable_fields_ = ['frame', 'func']
    def __init__(self, frame, func):
        self.frame = frame
        self.func = func

    def call(self, argv):
        argc = len(self.func.args)
        if len(argv) < argc:
            raise space.Error(u"closure requires %d arguments" % argc)
        frame = ActivationRecord(self.frame.module, self.frame)
        for i in range(argc):
            frame.var[self.func.args[i]] = argv[i]
        return interpret(self.func.body, frame)

class Generator(space.Object):
    _immutable_fields_ = ['tmp', 'frame']
    def __init__(self, block, tmp, frame, loop_break, op_i):
        self.block = block
        self.tmp = tmp
        self.frame = frame
        self.loop_break = loop_break
        self.op_i = op_i

    def iter(self):
        return self

@Generator.builtin_method
def next(argv):
    self = argv[0]
    assert isinstance(self, Generator)
    if len(argv) > 1:
        self.tmp[self.op_i] = argv[1]
    else:
        self.tmp[self.op_i] = space.null
    try:
        interpret_body(self.block, self.tmp, self.frame, self.loop_break)
        raise StopIteration()
    except YieldIteration as yi:
        self.block = yi.block
        self.loop_break = yi.loop_break
        self.op_i = yi.op_i
        return yi.value

class YieldIteration(Exception):
    _immutable_fields_ = ['block', 'loop_break', 'op_i', 'value']
    def __init__(self, block, loop_break, op_i, value):
        self.block = block
        self.loop_break = loop_break
        self.op_i = op_i
        self.value = value

class Block:
    _immutable_fields_ = ['index', 'contents[*]']

    def __init__(self, index, contents):
        self.index = index
        self.contents = None
        self.contents_mut = []

    def __iter__(self):
        return iter(self.contents)

    def __getitem__(self, index):
        return self.contents[index]

    def __len__(self):
        return len(self.contents)

    def append(self, op):
        assert isinstance(op, Op)
        self.contents_mut.append(op)

    def freeze(self):
        self.contents = self.contents_mut[:]
        self.contents_mut = None

#    def label(self):
#        return "b" + str(self.index)
#
#    def repr(self):
#        out = "b" + str(self.index) + ":"
#        for op in self:
#            out += '\n    '
#            out += op.repr()
#        return out

class Scope:
    def __init__(self, parent=None):
        self.blocks = []
        self.block = self.new_block()
        self.capture_catch = []
        self.functions = []
        self.bodies = []
        self.chain = []
        self.start = None
        self.stop = None
        self.is_generator = False
        self.loop_stack = []

    def new_block(self):
        block = Block(len(self.blocks), [])
        self.blocks.append(block)
        return block

    def new_function(self, argv, body):
        func = Function(argv)
        self.functions.append(func)
        self.bodies.append(body)
        return self.add(func)

    def new_label(self):
        if len(self.block.contents_mut) > 0:
            exit = self.new_block()
            self.add(Jump(exit))
            self.block = exit
        return self.block

    def add(self, op):
        self.block.append(op)
        op.start = self.start
        op.stop = self.stop
        return op

    def capture(self, exp):
        if len(self.capture_catch) == 0:
            raise space.Error(u"%s: expecting capture" % exp.start.repr())
        cap = self.capture_catch
        self.capture_catch = []
        return cap

    def pull_chain(self):
        chain = self.chain
        self.chain = []
        return chain

    def close(self):
        return ProgramBody(self.blocks, self.functions, self.is_generator)

class Op:
    _immutable_fields_ = ['i', 'start', 'stop', 'then', 'exit', 'value', 'body', 'args[*]', 'values[*]', 'name', 'cond', 'dst', 'src', 'it', 'block', 'upscope', 'ref']
    i = 0
    start = None
    stop = None
#    def repr(self):
#        return str(self.__class__.__name__) + " " + self.args_str()
#
#    def args_str(self):
#        return "..."

class Assert(Op):
    _immutable_fields_ = ['i', 'start', 'stop', 'value']
    def __init__(self, value):
        self.value = value

class ValuedOp(Op):
    pass
#    def repr(self):
#        return str(self.i) + " = " + str(self.__class__.__name__) + " " + self.args_str()

class Function(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'args', 'body']
    def __init__(self, args):
        self.args = args
        self.body = None

class Call(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'callee', 'args[*]']
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args[:]
#
#    def args_str(self):
#        out = str(self.callee.i)
#        for a in self.args:
#            out += ", " + str(a.i)
#        return out

class Cond(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'cond', 'then', 'exit']
    def __init__(self, cond):
        self.cond = cond
        self.then = None
        self.exit = None
#
#    def args_str(self):
#        return str(self.cond.i) + ", " + self.then.label() + ", " + self.exit.label()

class Merge(Op):
    _immutable_fields_ = ['i', 'start', 'stop', 'dst', 'src']
    def __init__(self, dst, src):
        self.dst = dst
        self.src = src
#
#    def args_str(self):
#        return str(self.dst.i) + ", " + str(self.src.i)

class Jump(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'exit']
    def __init__(self, exit):
        self.exit = exit

class Iter(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'value']
    def __init__(self, value):
        self.value = value

# It could be that the 'next' should be like 'iter', and that this
# operation should supply contents of SetBreak instead.
class Next(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'it']
    def __init__(self, it):
        self.it = it

class SetBreak(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'block']
    def __init__(self, block):
        self.block = block

#    def args_str(self):
#        return self.exit.label()

class Constant(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'value']
    def __init__(self, value):
        self.value = value

class MakeList(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'values[*]']
    def __init__(self, values):
        self.values = values[:]

class GetAttr(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'value', 'name']
    def __init__(self, value, name):
        self.value = value
        self.name = name

class GetItem(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'value', 'index']
    def __init__(self, value, index):
        self.value = value
        self.index = index

class Variable(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'name']
    def __init__(self, name):
        self.name = name

#    def args_str(self):
#        return self.name

class Yield(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'value', 'block']
    def __init__(self, value, block):
        self.value = value
        self.block = block

class SetAttr(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'name', 'value']
    def __init__(self, obj, name, value):
        self.obj = obj
        self.name = name
        self.value = value

class SetItem(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'index', 'value']
    def __init__(self, obj, index, value):
        self.obj = obj
        self.index = index
        self.value = value

class SetLocal(ValuedOp):
    _immutable_fields_ = ['i', 'start', 'stop', 'name', 'value', 'upscope']
    def __init__(self, name, value, upscope):
        assert isinstance(name, unicode)
        assert isinstance(value, ValuedOp)
        self.name = name
        self.value = value
        self.upscope = upscope

class Return(Op):
    _immutable_fields_ = ['i', 'start', 'stop', 'ref']
    def __init__(self, ref):
        self.ref = ref

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

def interpret(prog, frame):
    block = prog.blocks[0]
    tmp = []
    for i in range(prog.tmpc):
        tmp.append(space.null)
    for func in prog.functions:
        tmp[func.i] = Closure(frame, func)
    #for blk in prog.blocks:
    #    print blk.repr()
    if prog.is_generator:
        return Generator(block, tmp, frame, None, 0)
    return interpret_body(block, tmp, frame, None)

def get_printable_location(pc, block, loop_break, cl_frame_module):
    if loop_break is None:
        return "pc=%d block=%d cl_frame_module=%s" % (pc, block.index, cl_frame_module.repr().encode('utf-8'))
    return "pc=%d block=%d loop_break=%d cl_frame_module=%s" % (pc, block.index, loop_break.index, cl_frame_module.repr().encode('utf-8'))

def get_printable_location(pc, block, loop_break):
    if loop_break is None:
        return "pc=%d block=%d" % (pc, block.index)
    return "pc=%d block=%d loop_break=%d" % (pc, block.index, loop_break.index)

jitdriver = jit.JitDriver(
    greens=['pc', 'block', 'loop_break'],#, 'cl_frame.module'],
    reds=['cl_frame', 'frame'],
    virtualizables = ['frame'], # XXX
    get_printable_location=get_printable_location)
def interpret_body(block, t, cl_frame, loop_break):
    frame = Frame(t)
    pc = 0
    try:
        while pc < len(block):
            try:
                jitdriver.jit_merge_point(
                    pc=pc, block=block, loop_break=loop_break,
                    cl_frame=cl_frame, frame=frame)
                module = jit.promote(cl_frame.module)
                op = block[pc]
                pc += 1
                if isinstance(op, Call):
                    callee = frame.load(op.callee.i)
                    argv = []
                    for arg in op.args:
                        argv.append(frame.load(arg.i))
                    frame.store(op.i, callee.call(argv))
                elif isinstance(op, Assert):
                    if space.is_false(frame.load(op.value.i)):
                        raise space.Error(u"Assertion error")
                elif isinstance(op, Cond):
                    pc = 0
                    if space.is_false(frame.load(op.cond.i)):
                        block = op.exit
                    else:
                        block = op.then
                elif isinstance(op, Jump):
                    pc = 0
                    block = op.exit
                elif isinstance(op, Next):
                    frame.store(op.i, frame.load(op.it.i).callattr(u'next', []))
                elif isinstance(op, Yield):
                    raise YieldIteration(op.block, loop_break, op.i, frame.load(op.value.i))
                elif isinstance(op, SetBreak):
                    loop_break = op.block
                elif isinstance(op, Iter):
                    frame.store(op.i, frame.load(op.value.i).iter())
                elif isinstance(op, Constant):
                    frame.store(op.i, op.value)
                elif isinstance(op, Variable):
                    frame.store(op.i, lookup(module, cl_frame, op.name))
                elif isinstance(op, Merge):
                    frame.store(op.dst.i, frame.load(op.src.i))
                elif isinstance(op, Function):
                    pass
                elif isinstance(op, MakeList):
                    contents = []
                    for val in op.values:
                        contents.append(frame.load(val.i))
                    frame.store(op.i, space.List(contents))
                elif isinstance(op, GetAttr):
                    frame.store(op.i, frame.load(op.value.i).getattr(op.name))
                elif isinstance(op, GetItem):
                    frame.store(op.i, frame.load(op.value.i).getitem(frame.load(op.index.i)))
                elif isinstance(op, SetAttr):
                    frame.store(op.i, frame.load(op.obj.i).setattr(op.name, frame.load(op.value.i)))
                elif isinstance(op, SetItem):
                    frame.store(op.i, frame.load(op.obj.i).setitem(
                        frame.load(op.index.i),
                        frame.load(op.value.i)))
                elif isinstance(op, SetLocal):
                    frame.store(op.i, set_local(module, cl_frame, op.name, frame.load(op.value.i), op.upscope))
                elif isinstance(op, Return):
                    return frame.load(op.ref.i)
                else:
                    raise space.Error(u"spaced out")
            except StopIteration as stopiter:
                if loop_break is not None:
                    block = loop_break
                    loop_break = None
                    continue
                op = block[pc-1]
                error = space.Error(u"stop iteration")
                error.stacktrace.append((cl_frame, op.start, op.stop))
                raise error
        raise space.Error(u"crappy compiler")
    except space.Error as e:
        op = block[pc-1]
        e.stacktrace.append((cl_frame, op.start, op.stop))
        raise e



def lookup(module, frame, name):
    if frame.parent is None:
        return module.getattr(name)
    if name in frame.var:
        return frame.var[name]
    return lookup(module, frame.parent, name)

def set_local(module, frame, name, value, upscope):
    if frame.parent is None:
        return module.setattr(name, value)
    elif upscope:
        if name in frame.var:
            frame.var[name] = value
            return value
        else:
            return set_local(module, frame.parent, name, value, upscope)
    else:
        frame.var[name] = value
        return value

def assert_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error(u"no translation for %s with length != 2" % exp.name)
    val = translate(env, exp.exps[1])
    env.add(Assert(val))
    return val

def func_macro(env, exp):
    argv = []
    for i in range(1, len(exp.exps)):
        arg = exp.exps[i]
        if isinstance(arg, reader.Literal) and arg.name == u'symbol':
            argv.append(arg.value)
        else:
            raise space.Error(u"%s: expected symbol inside func" % arg.start.repr())
    body = env.capture(exp)
    return env.new_function(argv, body)

def if_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error(u"no translation for %s with length != 2" % exp.name)
    chain = env.pull_chain()
    cond = Cond(translate(env, exp.exps[1]))
    env.add(cond)
    cond.then = env.block = env.new_block()
    if len(chain) > 0:
        first = chain[0]
        if len(chain) > 1 and macro_name(first.exps[0]) != u'else' and len(first.exps) != 1:
            raise space.Error(u"%s: non-else longer chains not supported" % exp.start.repr())
        cond.exit = env.block = env.new_block()
        exit = env.new_block()
        val = translate_flow(env, first.capture)
        env.add(Merge(cond, val))
        env.add(Jump(exit))
        env.block = cond.then
    else:
        cond.exit = exit = env.new_block()
    val = translate_flow(env, env.capture(exp))
    env.add(Merge(cond, val))
    env.add(Jump(exit))
    env.block = exit
    return cond

def return_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error(u"no translation for %s with length != 2" % exp.name)
    return env.add(Return(translate(env, exp.exps[1])))

def while_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error(u"no translation for %s with length != 2" % exp.name)
    current_loop = (loop, exit, _) = (env.new_label(), env.new_block(), False)
    env.loop_stack.append(current_loop)

    loop = env.new_label()
    cond = env.add(Cond(translate(env, exp.exps[1])))
    cond.then = env.block = env.new_block()
    cond.exit = env.new_block()
    val = translate_flow(env, env.capture(exp))
    env.add(Merge(cond, val))
    env.add(Jump(loop))
    env.block = cond.exit
    loop_exit(env)
    return cond

def and_macro(env, exp):
    if len(exp.exps) != 3:
        raise space.Error(u"no translation for %s with length != 3" % exp.name)
    val = translate(env, exp.exps[1])
    cond = env.add(Cond(val))
    cond.then = env.block = env.new_block()
    cond.exit = env.new_block()
    env.add(Merge(val, translate(env, exp.exps[2])))
    env.add(Jump(cond.exit))
    env.block = cond.exit
    return val

def or_macro(env, exp):
    if len(exp.exps) != 3:
        raise space.Error(u"no translation for %s with length != 3" % exp.name)
    val = translate(env, exp.exps[1])
    cond = env.add(Cond(val))
    cond.exit = env.block = env.new_block()
    cond.then = env.new_block()
    env.add(Merge(val, translate(env, exp.exps[2])))
    env.add(Jump(cond.then))
    env.block = cond.then
    return val

def syntax_chain(env, exp):
    if len(exp.exps) < 3:
        raise space.Error(u"no translation for %s with length < 3" % exp.name)
    and_ = Variable(u'and')
    if len(exp.exps) > 3:
        env.add(and_)
    lhs = translate(env, exp.exps[0])
    op = translate(env, exp.exps[1])
    rhs = translate(env, exp.exps[2])
    res = env.add(Call(op, [lhs, rhs]))
    i = 3
    while i < len(exp.exps):
        lhs = rhs
        op = translate(env, exp.exps[i])
        rhs = translate(env, exp.exps[i+1])
        res = env.add(Call(and_, [
            res,
            env.add(Call(op, [lhs, rhs]))]))
        i += 2
    return res

def for_macro(env, exp):
    if len(exp.exps) != 3:
        raise space.Error(u"no translation for %s with length != 2" % exp.name)
    var = exp.exps[1]
    if not isinstance(var, reader.Literal):
        raise space.Error(u"%s: format: for variable exp" % exp.start.repr())
    it = env.add(Iter(translate(env, exp.exps[2])))

    current_loop = (loop, exit, _) = (env.new_block(), env.new_block(), True)
    env.loop_stack.append(current_loop)
    cond = env.add(SetBreak(exit))

    env.add(Jump(loop))
    env.block = loop
    env.add(SetLocal(var.value, env.add(Next(it)), False))
    val = translate_flow(env, env.capture(exp))
    env.add(Merge(cond, val))
    env.add(Jump(loop))
    env.block = exit

    loop_exit(env)
    return cond

def loop_exit(env):
    _, exit, _ = env.loop_stack.pop(-1)
    if len(env.loop_stack) > 0 and env.loop_stack[-1][2]:
        env.add(SetBreak(env.loop_stack[-1][1]))

def break_macro(env, exp):
    if len(exp.exps) != 1:
        raise space.Error(u"%s: format: break" % exp.start.repr())
    if len(env.loop_stack) == 0:
        raise space.Error(u"%s: not inside a loop" % exp.start.repr())
    return env.add(Jump(env.loop_stack[-1][1]))

def continue_macro(env, exp):
    if len(exp.exps) != 1:
        raise space.Error(u"%s: format: continue" % exp.start.repr())
    if len(env.loop_stack) == 0:
        raise space.Error(u"%s: not inside a loop" % exp.start.repr())
    return env.add(Jump(env.loop_stack[-1][0]))

def yield_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error(u"%s: format: yield expr" % exp.start.repr())
    env.is_generator = True
    val = translate(env, exp.exps[1])
    yield_ = env.add(Yield(val, env.new_block()))
    env.block = yield_.block
    return yield_

def from_macro(env, exp):
    if len(exp.exps) == 2:
        exp.exps.extend(env.capture(exp))
    if len(exp.exps) <= 2:
        raise space.Error(u"%s: format: from expr symbol..." % exp.start.repr())
    val = translate(env, exp.exps[1])
    for attr in exp.exps[2:]:
        if isinstance(attr, reader.Literal) and attr.name == u'symbol':
            var = env.add(GetAttr(val, attr.value))
            env.add(SetLocal(attr.value, var, False))
        else:
            raise space.Error(u"%s: expected symbol" % attr.start.repr())
    return val

macros = {
    u'break': break_macro,
    u'continue': continue_macro,
    u'assert': assert_macro,
    u'func': func_macro,
    u'for': for_macro,
    u'if': if_macro,
    u'return': return_macro,
    u'while': while_macro,
    u'and': and_macro,
    u'or': or_macro,
    u'yield': yield_macro,
    u'from': from_macro,
}
chain_macros = [u'else']

def macro_name(exp):
    if isinstance(exp, reader.Expr):
        if exp.name == u'form' and len(exp.exps) > 0:
            first = exp.exps[0]
            if isinstance(first, reader.Literal) and first.name == u'symbol':
                return first.value
    return u""

def translate_flow(env, exps):
    val = None
    for chain in chains(exps):
        val = translate_chain(env, chain)
    assert val is not None
    return val

def translate_map(env, exps):
    res = []
    for chain in chains(exps):
        res.append(translate_chain(env, chain))
    return res

def chains(exps):
    out = []
    chain = None
    for exp in exps:
        if chain is None:
            chain = [exp]
        elif macro_name(exp) in chain_macros:
            chain.append(exp)
        else:
            out.append(chain)
            chain = [exp]
    if chain is not None:
        out.append(chain)
    return out

def translate_chain(env, chain):
    chain_above = env.chain
    exp = chain.pop(0)
    env.chain = chain
    val = translate(env, exp)
    if len(env.chain) > 0:
        raise space.Error(u"%s: chain without receiver" % exp.start.repr())
    env.chain = chain_above
    return val

def translate(env, exp):
    start, stop = env.start, env.stop
    env.start, env.stop = exp.start, exp.stop
    res = translate_(env, exp)
    env.start, env.stop = start, stop
    return res

def translate_(env, exp):
    if isinstance(exp, reader.Literal):
        if exp.name == u'string':
            return env.add(Constant(space.from_ustring(exp.value)))
        elif exp.name == u'int':
            return env.add(Constant(space.Integer(int(exp.value.encode('utf-8')))))
        elif exp.name == u'hex':
            return env.add(Constant(space.Integer(int(exp.value[2:].encode('utf-8'), 16))))
        elif exp.name == u'float':
            return env.add(Constant(space.Float(float(exp.value.encode('utf-8')))))
        elif exp.name == u'symbol':
            return env.add(Variable(exp.value))
        raise space.Error(u"no translation for " + exp.name)
    assert isinstance(exp, reader.Expr), exp.__class__.__name__
    if exp.name == u'form' and len(exp.exps) > 0:
        if macro_name(exp) in macros:
            if len(exp.capture) > 0:
                env.capture_catch = exp.capture
            res = macros[macro_name(exp)](env, exp)
            if len(exp.capture) > 0 and len(env.capture_catch) > 0:
                raise space.Error(u"%s: capture without receiver" % exp.start.repr())
            return res
        # callattr goes here, if it'll be needed
        args = translate_map(env, exp.exps)
        callee = args.pop(0)
        args.extend(translate_map(env, exp.capture))
        return env.add(Call(callee, args))
    elif exp.name == u'list':
        return env.add(MakeList(translate_map(env, exp.exps)))
    elif exp.name == u'attr' and len(exp.exps) == 2:
        lhs, name = exp.exps
        lhs = translate(env, lhs)
        if not isinstance(name, reader.Literal):
            raise space.Error(u"%s: bad attribute expr" % exp.repr())
        return env.add(GetAttr(lhs, name.value))
        sym.value
    elif exp.name == u'index' and len(exp.exps) == 2:
        lhs, rhs = exp.exps
        lhs = translate(env, lhs)
        rhs = translate(env, rhs)
        return env.add(GetItem(lhs, rhs))
    elif exp.name == u'let' or exp.name == u'set':
        lhs, rhs = exp.exps
        rhs = translate(env, rhs)
        return store_value(env, lhs, rhs, exp.name == u'set')
    elif exp.name == u'aug' and len(exp.exps) == 3:
        aug, lhs, rhs = exp.exps
        if not isinstance(aug, reader.Literal):
            raise space.Error(u"%s: bad augmented expr" % exp.repr())
        rhs = translate(env, rhs)
        return store_aug_value(env, aug, lhs, rhs)
    elif exp.name == u'chain':
        return syntax_chain(env, exp)
    raise space.Error(u"no translation for " + exp.name)

def store_value(env, lhs, value, upscope):
    if isinstance(lhs, reader.Literal) and lhs.name == u'symbol':
        return env.add(SetLocal(lhs.value, value, upscope))
    elif isinstance(lhs, reader.Expr) and lhs.name == u'attr' and  len(lhs.exps) == 2:
        obj, name = lhs.exps
        obj = translate(env, obj)
        assert isinstance(name, reader.Literal)
        return env.add(SetAttr(obj, name.value, value))
    elif isinstance(lhs, reader.Expr) and lhs.name == u'index' and  len(lhs.exps) == 2:
        obj, index = lhs.exps
        obj = translate(env, obj)
        index = translate(env, index)
        return env.add(SetItem(obj, index, value))
    else:
        raise space.Error(u"no translation for " + lhs.name)

def store_aug_value(env, aug, lhs, value):
    aug = env.add(Variable(aug.value))
    if isinstance(lhs, reader.Literal) and lhs.name == u'symbol':
        name = lhs.value
        value = env.add(Call(aug, [env.add(Variable(name)), value]))
        return env.add(SetLocal(name, value, True))
    elif isinstance(lhs, reader.Expr) and lhs.name == u'attr' and  len(lhs.exps) == 2:
        obj, name = lhs.exps
        assert isinstance(name, reader.Literal)
        obj = translate(env, obj)
        value = env.add(Call(aug, [env.add(GetAttr(obj, name.value)), value]))
        return env.add(SetAttr(obj, name.value, value))
    elif isinstance(lhs, reader.Expr) and lhs.name == u'index' and  len(lhs.exps) == 2:
        obj, index = lhs.exps
        obj = translate(env, obj)
        index = translate(env, index)
        value = env.add(Call(aug, [env.add(GetItem(obj, index)), value]))
        return env.add(SetItem(obj, index, value))
    else:
        raise space.Error(u"no translation for " + lhs.name)

def build_closures(parent):
    for i in range(len(parent.functions)):
        env = Scope(parent)
        func = parent.functions[i]
        translate_flow(env, parent.bodies[i])
        w = env.add(Constant(space.null))
        env.add(Return(w))
        build_closures(env)
        func.body = env.close()

def to_program(exps):
    env = Scope()
    if len(exps) == 0:
        env.add(Return(env.add(Constant(space.null))))
        return Program(env.close())
    value = translate_flow(env, exps)
    env.add(Return(value))
    build_closures(env)
    return Program(env.close())
