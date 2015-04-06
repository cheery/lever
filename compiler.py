import base
import reader
import space

class Program(space.Object):
    def __init__(self, blocks):
        self.blocks = blocks
        self.tmpc = 0
        for block in blocks:
            for op in block:
                if isinstance(op, ValuedOp):
                    op.i = self.tmpc
                    self.tmpc += 1

    def call(self, argv):
        return interpret(self, argv)

class Block:
    def __init__(self, contents):
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

class Scope:
    def __init__(self):
        self.blocks = []
        self.block = self.new_block()

    def new_block(self):
        block = Block([])
        self.blocks.append(block)
        return block

    def add(self, op):
        self.block.append(op)
        return op

class Op:
    i = 0

class ValuedOp(Op):
    pass

class Call(ValuedOp):
    def __init__(self, callee, args):
        self.callee = callee
        self.args = args

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

class Global(ValuedOp):
    def __init__(self, name):
        self.name = name

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

class SetGlobal(ValuedOp):
    def __init__(self, name, value):
        assert isinstance(name, str)
        assert isinstance(value, ValuedOp)
        self.name = name
        self.value = value

class Return(Op):
    def __init__(self, ref):
        self.ref = ref

def interpret(prog, argv):
    if len(argv) < 1:
        raise space.Error("Module required as an argument for interpret()")
    block = prog.blocks[0]
    module = argv[0]
    pc = 0
    tmp = []
    for i in range(prog.tmpc):
        tmp.append(space.null)
    var = {}
    while pc < len(block):
        op = block[pc]
        if isinstance(op, Call):
            callee = tmp[op.callee.i]
            argv = []
            for arg in op.args:
                argv.append(tmp[arg.i])
            tmp[op.i] = callee.call(argv)
        elif isinstance(op, Constant):
            tmp[op.i] = op.value
        elif isinstance(op, Global):
            tmp[op.i] = module.getattr(op.name)
        elif isinstance(op, GetAttr):
            tmp[op.i] = tmp[op.value.i].getattr(op.name)
        elif isinstance(op, GetItem):
            tmp[op.i] = tmp[op.value.i].getitem(op.index.i)
        elif isinstance(op, SetAttr):
            tmp[op.i] = tmp[op.obj.i].setattr(op.name, tmp[op.value.i])
        elif isinstance(op, SetItem):
            tmp[op.i] = tmp[op.obj.i].setitem(tmp[op.index.i], tmp[op.value.i])
        elif isinstance(op, SetGlobal):
            tmp[op.i] = module.setattr(op.name, tmp[op.value.i])
        elif isinstance(op, Return):
            return tmp[op.ref.i]
        else:
            raise space.Error("spaced out")
        pc += 1
    raise space.Error("crappy compiler")


def func_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error("no translation for " + exp.name + " with length != 2")
    return env.add(Return(translate(env, exp.exps[1])))

def if_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error("no translation for " + exp.name + " with length != 2")
    return env.add(Return(translate(env, exp.exps[1])))

def return_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error("no translation for " + exp.name + " with length != 2")
    return env.add(Return(translate(env, exp.exps[1])))

def while_macro(env, exp):
    if len(exp.exps) != 2:
        raise space.Error("no translation for " + exp.name + " with length != 2")
    return env.add(Return(translate(env, exp.exps[1])))

macros = {
    'func': func_macro,
    'if': if_macro,
    'return': return_macro,
    'while': while_macro,
}

def translate(env, exp):
    if isinstance(exp, reader.Literal):
        if exp.name == 'string':
            return env.add(Constant(space.String(exp.value)))
        elif exp.name == 'int':
            return env.add(Constant(space.Integer(int(exp.value))))
        elif exp.name == 'symbol':
            return env.add(Global(exp.value))
        raise space.Error("no translation for " + exp.name)
    assert isinstance(exp, reader.Expr)
    if exp.name == 'form' and len(exp.exps) > 0:
        lhs = exp.exps[0]
        if isinstance(lhs, reader.Literal) and lhs.value in macros:
            res = macros[lhs.value](env, exp)
            return res
        # callattr goes here, if it'll be needed
        callee = translate(env, lhs)
        args = []
        for i in range(1, len(exp.exps)):
            args.append(translate(env, exp.exps[i]))
        for arg in exp.capture:
            args.append(translate(env, arg))
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
        if isinstance(lhs, reader.Literal) and lhs.name == 'symbol':
            return env.add(SetGlobal(lhs.value, rhs))
        elif isinstance(lhs, reader.Expr) and lhs.name == 'attr' and  len(lhs.exps) == 2:
            obj, name = lhs.exps
            obj = translate(env, obj)
            assert isinstance(name, reader.Literal)
            return env.add(SetAttr(obj, name.value, rhs))
        elif isinstance(lhs, reader.Expr) and lhs.name == 'index' and  len(lhs.exps) == 2:
            obj, index = lhs.exps
            obj = translate(env, obj)
            index = translate(env, index)
            return env.add(SetItem(obj, index, rhs))
        else:
            raise space.Error("no translation for " + lhs.name)
    raise space.Error("no translation for " + exp.name)

def to_program(exps):
    if len(exps) == 0:
        w = Constant(space.null)
        x = Return(w)
        return Program([Block([w, x])])
    env = Scope()
    value = translate(env, exps[0])
    for i in range(1, len(exps)):
        value = translate(env, exps[i])
    env.add(Return(value))
    return Program(env.blocks)
