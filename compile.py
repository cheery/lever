from bincode.encoder import ConstantTable, dump_function
from spacing_functions import functions
from compiler_program import Function, Block, Constant, Op
import grammarlang
import os
import sys

def main():
    for name in sys.argv[1:]:
        functions = []
        env = Scope(functions)
        entry = ScopeBlock(env)
        result = parser.from_file(globals(), entry, name)
        entry.op(result.loc, 'return', result)
        assert env.close() == functions[0]

        consttab = ConstantTable()
        functions = [func.dump(consttab) for func in functions]
        dump_function(os.path.splitext(name)[0] + '.lic',
            functions=functions,
            constants=consttab.constants)

class Scope(object):
    def __init__(self, functions):
        self.blocks = []
        self.functions = functions
        self.localv = []
        self.flags = 0x0
        self.argc = 0

    def close(self):
        index = len(self.functions)
        func = Function(index, self.flags, self.argc, self.localv, self.blocks)
        self.functions.append(func)
        return func

# Represents single 'block level' in the source code
# That means structured control flow changes the block pointer.
class ScopeBlock(object):
    def __init__(self, scope):
        self.scope = scope
        self.block = Block(0, [], set())
        scope.blocks.append(self.block)

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
    name = Constant(loc, name.value)
    return env.op(loc, 'getattr', obj, name)

def post_getitem(env, loc, obj, index):
    return env.op(loc, 'getitem', obj, index)

def post_lookup(env, loc, symbol):
    # XXX: replace with real lookup
    return env.op(loc, 'getglob', Constant(symbol.value))

def post_int(env, loc, num):
    return env.op(loc, 'constant', Constant(int(num.value)))

def post_float(env, loc, num):
    return env.op(loc, 'constant', Constant(float(num.value)))

def post_string(env, loc, string):
    return env.op(loc, 'constant', Constant(string.value))

def post_pass(env, loc, val):
    return val

def post_tuple(env, loc, *args):
    return args

if __name__=='__main__': main()
