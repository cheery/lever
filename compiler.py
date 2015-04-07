import base
import reader
import space

# specialize.argtypes

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
            raise space.Error("program expects module as an argument")
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
            raise space.Error("closure requires " + str(argc) + " arguments")
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

    def label(self):
        return "b" + str(self.index)

    def repr(self):
        out = "b" + str(self.index) + ":"
        for op in self:
            out += '\n    '
            out += op.repr()
        return out

class Scope:
    def __init__(self, parent=None):
        self.blocks = []
        self.block = self.new_block()
        self.capture_catch = []
        self.functions = []
        self.bodies = []
        self.chain = []

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
        return op

    def capture(self, exp):
        if len(self.capture_catch) == 0:
            raise space.Error(exp.start.str() + ": expecting capture")
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
    def repr(self):
        return str(self.__class__.__name__) + " " + self.args_str()

    def args_str(self):
        return "..."

class ValuedOp(Op):
    def repr(self):
        return str(self.i) + " = " + str(self.__class__.__name__) + " " + self.args_str()

class Function(ValuedOp):
    def __init__(self, args):
        self.args = args
        self.body = None

class Call(ValuedOp):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

    def args_str(self):
        out = str(self.callee.i)
        for a in self.args:
            out += ", " + str(a.i)
        return out

class Cond(ValuedOp):
    def __init__(self, cond):
        self.cond = cond
        self.then = None
        self.exit = None

    def args_str(self):
        return str(self.cond.i) + ", " + self.then.label() + ", " + self.exit.label()

class Merge(Op):
    def __init__(self, dst, src):
        self.dst = dst
        self.src = src

    def args_str(self):
        return str(self.dst.i) + ", " + str(self.src.i)

class Jump(ValuedOp):
    def __init__(self, exit):
        self.exit = exit

    def args_str(self):
        return self.exit.label()

class Constant(ValuedOp):
    def __init__(self, value):
        self.value = value

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

    def args_str(self):
        return self.name

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
        assert isinstance(name, str)
        assert isinstance(value, ValuedOp)
        self.name = name
        self.value = value
        self.upscope = upscope

class Return(Op):
    def __init__(self, ref):
        self.ref = ref

def interpret(prog, frame):
    block = prog.blocks[0]
    pc = 0
    tmp = []
    for i in range(prog.tmpc):
        tmp.append(space.null)
    for func in prog.functions:
        tmp[func.i] = Closure(frame, func)
    #for blk in prog.blocks:
    #    print blk.repr()
    while pc < len(block):
        op = block[pc]
        pc += 1
        if isinstance(op, Call):
            callee = tmp[op.callee.i]
            argv = []
            for arg in op.args:
                argv.append(tmp[arg.i])
            tmp[op.i] = callee.call(argv)
        elif isinstance(op, Cond):
            pc = 0
            if space.is_false(tmp[op.cond.i]):
                block = op.exit
            else:
                block = op.then
        elif isinstance(op, Jump):
            pc = 0
            block = op.exit
        elif isinstance(op, Constant):
            tmp[op.i] = op.value
        elif isinstance(op, Variable):
            tmp[op.i] = lookup(frame, op.name)
        elif isinstance(op, Merge):
            tmp[op.dst.i] = tmp[op.src.i]
        elif isinstance(op, Function):
            pass
        elif isinstance(op, GetAttr):
            tmp[op.i] = tmp[op.value.i].getattr(op.name)
        elif isinstance(op, GetItem):
            tmp[op.i] = tmp[op.value.i].getitem(op.index.i)
        elif isinstance(op, SetAttr):
            tmp[op.i] = tmp[op.obj.i].setattr(op.name, tmp[op.value.i])
        elif isinstance(op, SetItem):
            tmp[op.i] = tmp[op.obj.i].setitem(tmp[op.index.i], tmp[op.value.i])
        elif isinstance(op, SetLocal):
            tmp[op.i] = set_local(frame, op.name, tmp[op.value.i], op.upscope)
        elif isinstance(op, Return):
            return tmp[op.ref.i]
        else:
            raise space.Error("spaced out")
    print block.repr(), pc
    raise space.Error("crappy compiler")

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

def func_macro(env, exp):
    argv = []
    for i in range(1, len(exp.exps)):
        arg = exp.exps[i]
        if isinstance(arg, reader.Literal) and arg.name == 'symbol':
            argv.append(arg.value)
        else:
            raise space.Error(arg.start.str() + ": expected symbol inside func")
    body = env.capture(exp)
    return env.new_function(argv, body)

def if_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error("no translation for " + exp.name + " with length != 2")
    chain = env.pull_chain()
    cond = Cond(translate(env, exp.exps[1]))
    env.add(cond)
    cond.then = env.block = env.new_block()
    if len(chain) > 0:
        first = chain[0]
        if len(chain) > 1 and macro_name(first.exps[0]) != 'else' and len(first.exps) != 1:
            raise space.Error(exp.start.str() + ": non-else longer chains not supported")
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
        raise space.Error("no translation for " + exp.name + " with length != 2")
    return env.add(Return(translate(env, exp.exps[1])))

def while_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error("no translation for " + exp.name + " with length != 2")
    loop = env.new_label()
    cond = Cond(translate(env, exp.exps[1]))
    env.add(cond)
    cond.then = env.block = env.new_block()
    cond.exit = env.new_block()
    val = translate_flow(env, env.capture(exp))
    env.add(Merge(cond, val))
    env.add(Jump(loop))
    env.block = cond.exit
    return cond

macros = {
    'func': func_macro,
    'if': if_macro,
    'return': return_macro,
    'while': while_macro,
}
chain_macros = ['else']

def macro_name(exp):
    if isinstance(exp, reader.Expr):
        if exp.name == 'form' and len(exp.exps) > 0:
            first = exp.exps[0]
            if isinstance(first, reader.Literal) and first.name == 'symbol':
                return first.value
    return ""

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
        raise space.Error(exp.start.str() + ": chain without receiver")
    env.chain = chain_above
    return val

def translate(env, exp):
    if isinstance(exp, reader.Literal):
        if exp.name == 'string':
            return env.add(Constant(space.String(exp.value)))
        elif exp.name == 'int':
            return env.add(Constant(space.Integer(int(exp.value))))
        elif exp.name == 'symbol':
            return env.add(Variable(exp.value))
        raise space.Error("no translation for " + exp.name)
    assert isinstance(exp, reader.Expr)
    if exp.name == 'form' and len(exp.exps) > 0:
        if macro_name(exp) in macros:
            if len(exp.capture) > 0:
                env.capture_catch = exp.capture
            res = macros[macro_name(exp)](env, exp)
            if len(exp.capture) > 0 and len(env.capture_catch) > 0:
                raise space.Error(exp.start.str() + ": capture without receiver")
            return res
        # callattr goes here, if it'll be needed
        args = translate_map(env, exp.exps)
        callee = args.pop(0)
        args.extend(translate_map(env, exp.capture))
        return env.add(Call(callee, args))
    elif exp.name == 'attr' and len(exp.exps) == 2:
        lhs, name = exp.exps
        lhs = translate(env, lhs)
        assert isinstance(name, reader.Literal)
        return env.add(GetAttr(lhs, name.value))
        sym.value
    elif exp.name == 'index' and len(exp.exps) == 2:
        lhs, rhs = exp.exps
        lhs = translate(env, lhs)
        rhs = translate(env, rhs)
        return env.add(GetItem(lhs, rhs))
    elif exp.name == 'let' or exp.name == 'set':
        lhs, rhs = exp.exps
        rhs = translate(env, rhs)
        return store_value(env, lhs, rhs, exp.name == 'set')
    elif exp.name == 'aug' and len(exp.exps) == 3:
        aug, lhs, rhs = exp.exps
        assert isinstance(aug, reader.Literal)
        rhs = translate(env, rhs)
        return store_aug_value(env, aug, lhs, rhs)
    raise space.Error("no translation for " + exp.name)

def store_value(env, lhs, value, upscope):
    if isinstance(lhs, reader.Literal) and lhs.name == 'symbol':
        return env.add(SetLocal(lhs.value, value, upscope))
    elif isinstance(lhs, reader.Expr) and lhs.name == 'attr' and  len(lhs.exps) == 2:
        obj, name = lhs.exps
        obj = translate(env, obj)
        assert isinstance(name, reader.Literal)
        return env.add(SetAttr(obj, name.value, value))
    elif isinstance(lhs, reader.Expr) and lhs.name == 'index' and  len(lhs.exps) == 2:
        obj, index = lhs.exps
        obj = translate(env, obj)
        index = translate(env, index)
        return env.add(SetItem(obj, index, value))
    else:
        raise space.Error("no translation for " + lhs.name)

def store_aug_value(env, aug, lhs, value):
    aug = env.add(Variable(aug.value))
    if isinstance(lhs, reader.Literal) and lhs.name == 'symbol':
        name = lhs.value
        value = env.add(Call(aug, [env.add(Variable(name)), value]))
        return env.add(SetLocal(name, value, True))
    elif isinstance(lhs, reader.Expr) and lhs.name == 'attr' and  len(lhs.exps) == 2:
        obj, name = lhs.exps
        assert isinstance(name, reader.Literal)
        obj = translate(env, obj)
        value = env.add(Call(aug, [env.add(GetAttr(obj, name.value)), value]))
        return env.add(SetAttr(obj, name.value, value))
    elif isinstance(lhs, reader.Expr) and lhs.name == 'index' and  len(lhs.exps) == 2:
        obj, index = lhs.exps
        obj = translate(env, obj)
        index = translate(env, index)
        value = env.add(Call(aug, [env.add(GetItem(obj, index)), value]))
        return env.add(SetItem(obj, index, value))
    else:
        raise space.Error("no translation for " + lhs.name)

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
