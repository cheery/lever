from bincode.encoder import ConstantTable, dump_function
from spacing_functions import functions
from compiler_program import Function, Block, Constant, Op
import grammarlang
import os
import sys

def main(debug=False):
    for name in sys.argv[1:]:
        functions = []
        env = Scope(None, functions)
        entry = ScopeBlock(env)
        result = parser.from_file(globals(), entry, name)
        entry.op(result.loc, 'return', result)
        assert env.close() == functions[0]
        consttab = ConstantTable()
        functions = [func.dump(consttab) for func in functions]
        if debug:
            from evaluator import optable
            for func in functions:
                print func[:-2]
                block = func[-1]
                pc = 0
                while pc < len(block):
                    opname, has_result, pattern, variadic = optable.dec[block[pc] >> 8]
                    px = pc + 1
                    pc = pc + 1 + block[pc] & 255
                    args = block[px:pc]
                    if has_result:
                        result = args.pop(0)
                        code = ' '.join(format_args(args, pattern, variadic, consttab.constants.keys()))
                        print "{:>2x}: {:2} = {:10} {}".format(px-1, result, opname, code)
                    else:
                        code = ' '.join(format_args(args, pattern, variadic, consttab.constants.keys()))
                        print "{:>2x}:      {:10} {}".format(px-1, opname, code)
        dump_function(os.path.splitext(name)[0] + '.lic',
            functions=functions,
            constants=consttab.constants)

def format_args(args, pattern, variadic, constants):
    pattern = pattern + [variadic]*(len(args) - len(pattern))
    for arg, pat in zip(args, pattern):
        if pat == 'vreg':
            yield "{:}".format(arg)
        elif pat in ('constant', 'string'):
            yield "{!r}({})".format(constants[arg], arg)
        else:
            yield "{}({:x})".format(pat, arg)

class Scope(object):
    def __init__(self, parent_block, functions):
        self.blocks = []
        self.functions = functions
        self.localv = []
        self.flags = 0x0
        self.argc = 0
        self.index = len(self.functions)
        self.functions.append(self)
        self.parent_block = parent_block

    def close(self):
        func = Function(self.index, self.flags, self.argc, self.localv, self.blocks)
        self.functions[self.index] = func
        return func

# Represents single 'block level' in the source code
# That means structured control flow changes the block pointer.
class ScopeBlock(object):
    def __init__(self, scope, parent=None):
        self.scope = scope
        self.block = Block(0, [], set())
        scope.blocks.append(self.block)
        self.parent = parent
        self.first = self.block

    def label(self):
        if len(self.block) == 0:
            return self.block
        self.block = Block(0, [], set())
        scope.blocks.append(self.block)

    def set_label(self, block):
        if block not in self.scope.blocks:
            self.scope.blocks.append(block)
        self.block = block

    def subscope(self):
        return Scope(self, self.scope.functions)

    def subblock(self):
        return ScopeBlock(self.scope, self)

    def op(self, loc, name, *args):
        op = Op(loc, name, args)
        self.block.append(op)
        return op

parser = grammarlang.load(functions, 'pyllisp.grammar')

def post_empty_list(env, loc):
    return []

def post_first(env, loc, item):
    return [item]

def post_append(env, loc, seq, item):
    seq.append(item)
    return seq

def post_binary(env, loc, lhs, op, rhs):
    # XXX: replace with lookup
    callee = env.op(loc, 'getglob', Constant(op.value))
    return env.op(loc, 'call', callee, lhs, rhs)

def post_prefix(env, loc, op, rhs):
    # XXX: replace with lookup
    callee = env.op(loc, 'getglob', Constant(op.value + "expr"))
    return env.op(loc, 'call', callee, rhs)

def post_call(env, loc, callee, args):
    return env.op(loc, 'call', callee, *args)

def post_getattr(env, loc, obj, name):
    return env.op(loc, 'getattr', obj, Constant(name.value))

def post_getitem(env, loc, obj, index):
    return env.op(loc, 'getitem', obj, index)

def post_lookup(env, loc, symbol):
    # XXX: replace with real lookup
    if symbol.value in env.scope.localv:
        index = env.scope.localv.index(symbol.value)
        return env.op(loc, 'getloc', index)
    return env.op(loc, 'getglob', Constant(symbol.value))

def post_int(env, loc, num):
    return env.op(loc, 'constant', Constant(int(num.value)))

def post_float(env, loc, num):
    return env.op(loc, 'constant', Constant(float(num.value)))

def post_string(env, loc, string):
    return env.op(loc, 'constant', Constant(string.value))

def post_list(env, loc, exprs):
    return env.op(loc, 'list', *exprs)

def post_pass(env, loc, val):
    return val

def post_tuple(env, loc, *args):
    return args

def pre_function(env, loc):
    return ScopeBlock(env.subscope())

def post_function(env, loc, bindings):
    env.scope.argc = len(bindings)
    parent = env.scope.parent_block
    return parent.op(loc, 'func', env.scope.close())

def post_return(env, loc, expr):
    env.op(loc, 'return', expr)
    return expr

def post_assign(env, loc, lhs, rhs):
    name = lhs.value
    if name not in env.scope.localv:
        env.scope.localv.append(name)
    index = env.scope.localv.index(name)
    return env.op(loc, 'setloc', index, rhs)

def post_binding(env, loc, symbol):
    env.scope.localv.append(symbol.value)

def pre_subblock(env, loc):
    return env.subblock()

def post_subblock(env, loc, result):
    return env, result

def post_if(env, loc, cond, (sub, sub_result)):
    exit = Block(0, [], set())
    result = env.op(loc, 'getglob', Constant('null'))
    env.op(loc, 'cond', cond, sub.first, exit)
    env.set_label(exit)
    sub.op(loc, 'move', result, sub_result)
    sub.op(loc, 'jump', exit)
    return result

if __name__=='__main__': main()
