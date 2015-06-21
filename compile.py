from bincode.encoder import ConstantTable, dump_function
from instruction_format import enc_code
from spacing_functions import functions
from compiler_program import Body, Block, Constant, Op, VOp
import grammarlang
import os
import sys

class Scope(object):
    def __init__(self):
        self.blocks = []
        self.functions = []
        self.localv = []
        self.flags = 0x0
        self.argc = 0

    def close(self):
        return Body(self.blocks, self.functions, self.localv, self.flags, self.argc)

# Represents single 'block level' in the source code
# That means structured control flow changes the block pointer.
class ScopeBlock(object):
    def __init__(self, scope):
        self.scope = scope
        self.block = Block(0, [], set())
        scope.blocks.append(self.block)

    def op(self, loc, name, *args):
        op = Op(loc, name, *args)
        self.block.append(op)
        return op

    def vop(self, loc, name, *args):
        op = VOp(loc, name, *args)
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
    callee = env.vop(loc, 'gglo', Constant(loc, op.value))
    return env.vop(loc, 'call', callee, lhs, rhs)

def post_prefix(env, loc, op, rhs):
    # XXX: replace with lookup
    callee = env.vop(loc, 'gglo', Constant(loc, op.value + "expr"))
    return env.vop(loc, 'call', callee, rhs)

def post_call(env, loc, callee, args):
    return env.vop(loc, 'call', callee, *args)

def post_getattr(env, loc, obj, name):
    name = Constant(loc, name.value)
    return env.vop(loc, 'gatr', obj, name)

def post_getitem(env, loc, obj, index):
    return env.vop(loc, 'gitm', obj, index)

def post_lookup(env, loc, symbol):
    # XXX: replace with real lookup
    return env.vop(loc, 'gglo', Constant(loc, symbol.value))

def post_int(env, loc, num):
    return env.vop(loc, 'cnst', Constant(loc, int(num.value)))

def post_float(env, loc, num):
    return env.vop(loc, 'cnst', Constant(loc, float(num.value)))

def post_string(env, loc, string):
    return env.vop(loc, 'cnst', Constant(loc, string.value))

def post_pass(env, loc, val):
    return val

def post_tuple(env, loc, *args):
    return args

def main():
    for name in sys.argv[1:]:
        env = Scope()
        entry = ScopeBlock(env)
        result = parser.from_file(globals(), entry, name)
        entry.op(result.loc, 'ret', result)

        consttab = ConstantTable()
        function = env.close().dump(consttab)
        dump_function(os.path.splitext(name)[0] + '.lic', function, consttab)

if __name__=='__main__': main()
