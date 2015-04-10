import base
import reader
import space

class ProgramBody:
    def __init__(self, blocks, functions):
        self.blocks = blocks
        self.functions = functions
        self.tmpc = 0
        for block in blocks:
            for op in block:
                if isinstance(op, ValuedOp):
                    op.i = self.tmpc
                    self.tmpc += 1

class ActivationRecord:
    def __init__(self, module, parent):
        self.var = {}
        self.module = module
        self.parent = parent

class Program(space.Object):
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

class Block:
    def __init__(self, index, contents):
        self.index = index
        self.contents = contents

    def __iter__(self):
        return iter(self.contents)

    def __getitem__(self, index):
        return self.contents[index]

    def __len__(self):
        return len(self.contents)

    def append(self, op):
        assert isinstance(op, Op)
        self.contents.append(op)

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
        if len(self.block.contents) > 0:
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
        return ProgramBody(self.blocks, self.functions)

class Op:
    i = 0
    start = None
    stop = None
#    def repr(self):
#        return str(self.__class__.__name__) + " " + self.args_str()
#
#    def args_str(self):
#        return "..."

class Assert(Op):
    def __init__(self, value):
        self.value = value

class ValuedOp(Op):
    pass
#    def repr(self):
#        return str(self.i) + " = " + str(self.__class__.__name__) + " " + self.args_str()

class Function(ValuedOp):
    def __init__(self, args):
        self.args = args
        self.body = None

class Call(ValuedOp):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args
#
#    def args_str(self):
#        out = str(self.callee.i)
#        for a in self.args:
#            out += ", " + str(a.i)
#        return out

class Cond(ValuedOp):
    def __init__(self, cond):
        self.cond = cond
        self.then = None
        self.exit = None
#
#    def args_str(self):
#        return str(self.cond.i) + ", " + self.then.label() + ", " + self.exit.label()

class Merge(Op):
    def __init__(self, dst, src):
        self.dst = dst
        self.src = src
#
#    def args_str(self):
#        return str(self.dst.i) + ", " + str(self.src.i)

class Jump(ValuedOp):
    def __init__(self, exit):
        self.exit = exit

class Iter(ValuedOp):
    def __init__(self, value):
        self.value = value

class Next(ValuedOp):
    def __init__(self, it):
        self.it = it

class SetBreak(ValuedOp):
    def __init__(self, block):
        self.block = block

class JumpBreak(Op):
    pass
#
#    def args_str(self):
#        return self.exit.label()

class Constant(ValuedOp):
    def __init__(self, value):
        self.value = value

class MakeList(ValuedOp):
    def __init__(self, values):
        self.values = values

class GetAttr(ValuedOp):
    def __init__(self, value, name):
        self.value = value
        self.name = name

class GetItem(ValuedOp):
    def __init__(self, value, index):
        self.value = value
        self.index = index

class Variable(ValuedOp):
    def __init__(self, name):
        self.name = name

#    def args_str(self):
#        return self.name

class SetAttr(ValuedOp):
    def __init__(self, obj, name, value):
        self.obj = obj
        self.name = name
        self.value = value

class SetItem(ValuedOp):
    def __init__(self, obj, index, value):
        self.obj = obj
        self.index = index
        self.value = value

class SetLocal(ValuedOp):
    def __init__(self, name, value, upscope):
        assert isinstance(name, unicode)
        assert isinstance(value, ValuedOp)
        self.name = name
        self.value = value
        self.upscope = upscope

class Return(Op):
    def __init__(self, ref):
        self.ref = ref

def interpret(prog, frame):
    block = prog.blocks[0]
    tmp = []
    for i in range(prog.tmpc):
        tmp.append(space.null)
    for func in prog.functions:
        tmp[func.i] = Closure(frame, func)
    #for blk in prog.blocks:
    #    print blk.repr()
    return interpret_body(block, tmp, frame)

def interpret_body(block, tmp, frame):
    loop_break = None
    pc = 0
    try:
        while pc < len(block):
            op = block[pc]
            pc += 1
            if isinstance(op, Call):
                callee = tmp[op.callee.i]
                argv = []
                for arg in op.args:
                    argv.append(tmp[arg.i])
                tmp[op.i] = callee.call(argv)
            elif isinstance(op, Assert):
                if space.is_false(tmp[op.value.i]):
                    raise space.Error(u"Assertion error")
            elif isinstance(op, Cond):
                pc = 0
                if space.is_false(tmp[op.cond.i]):
                    block = op.exit
                else:
                    block = op.then
            elif isinstance(op, Jump):
                pc = 0
                block = op.exit
            elif isinstance(op, JumpBreak):
                if loop_break is not None:
                    pc = 0
                    block = loop_break
                    loop_break = None
            elif isinstance(op, Next):
                tmp[op.i] = tmp[op.it.i].callattr(u'next', [])
            elif isinstance(op, SetBreak):
                loop_break = op.block
            elif isinstance(op, Iter):
                tmp[op.i] = tmp[op.value.i].iter()
            elif isinstance(op, Constant):
                tmp[op.i] = op.value
            elif isinstance(op, Variable):
                tmp[op.i] = lookup(frame, op.name)
            elif isinstance(op, Merge):
                tmp[op.dst.i] = tmp[op.src.i]
            elif isinstance(op, Function):
                pass
            elif isinstance(op, MakeList):
                contents = []
                for val in op.values:
                    contents.append(tmp[val.i])
                tmp[op.i] = space.List(contents)
            elif isinstance(op, GetAttr):
                tmp[op.i] = tmp[op.value.i].getattr(op.name)
            elif isinstance(op, GetItem):
                tmp[op.i] = tmp[op.value.i].getitem(tmp[op.index.i])
            elif isinstance(op, SetAttr):
                tmp[op.i] = tmp[op.obj.i].setattr(op.name, tmp[op.value.i])
            elif isinstance(op, SetItem):
                tmp[op.i] = tmp[op.obj.i].setitem(tmp[op.index.i], tmp[op.value.i])
            elif isinstance(op, SetLocal):
                tmp[op.i] = set_local(frame, op.name, tmp[op.value.i], op.upscope)
            elif isinstance(op, Return):
                return tmp[op.ref.i]
            else:
                raise space.Error(u"spaced out")
        raise space.Error(u"crappy compiler")
    except space.Error as e:
        op = block[pc-1]
        e.stacktrace.append((frame, op.start, op.stop))
        raise e
    except StopIteration as stopiter:
        if loop_break is not None:
            return interpret_body(loop_break, tmp, frame)
        op = block[pc-1]
        error = space.Error(u"stop iteration")
        error.stacktrace.append((frame, op.start, op.stop))
        raise error



def lookup(frame, name):
    if frame.parent is None:
        return frame.module.getattr(name)
    if name in frame.var:
        return frame.var[name]
    return lookup(frame.parent, name)

def set_local(frame, name, value, upscope):
    if frame.parent is None:
        return frame.module.setattr(name, value)
    elif upscope:
        if name in frame.var:
            frame.var[name] = value
            return value
        else:
            return set_local(frame.parent, name, value, upscope)
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
    loop = env.new_label()
    cond = env.add(Cond(translate(env, exp.exps[1])))
    cond.then = env.block = env.new_block()
    cond.exit = env.new_block()
    val = translate_flow(env, env.capture(exp))
    env.add(Merge(cond, val))
    env.add(Jump(loop))
    env.block = cond.exit
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
    loop = env.new_block()
    exit = env.new_block()
    cond = env.add(SetBreak(exit))
    env.add(Jump(loop))
    env.block = loop
    env.add(SetLocal(var.value, env.add(Next(it)), False))
    val = translate_flow(env, env.capture(exp))
    env.add(Merge(cond, val))
    env.add(Jump(loop))
    env.block = exit
    return cond

def break_macro(env, exp):
    if len(exp.exps) != 1:
        raise space.Error(u"%s: format: break" % exp.start.repr())
    return env.add(JumpBreak())

macros = {
    u'break': break_macro,
    u'assert': assert_macro,
    u'func': func_macro,
    u'for': for_macro,
    u'if': if_macro,
    u'return': return_macro,
    u'while': while_macro,
    u'and': and_macro,
    u'or': or_macro,
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
