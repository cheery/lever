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

def post_first(env, loc, item):
    return [item]

def post_append(env, loc, seq, item):
    seq.append(item)
    return seq

def post_lookup(env, loc, symbol):
    return None

def post_int(env, loc, num):
    return Constant(loc, int(num.value))

def post_float(env, loc, num):
    return Constant(loc, int(num.value))

def post_string(env, loc, string):
    return Constant(loc, string.value)

def post_pass(env, loc, val):
    return val

def post_tuple(env, loc, *args):
    return args

def main():
    for name in sys.argv[1:]:
        env = Scope()
        entry = ScopeBlock(env)
        result = parser.from_file(globals(), env, name)
        entry.op(result.loc, 'ret', result)

        consttab = ConstantTable()
        function = env.close().dump(consttab)
        dump_function(os.path.splitext(name)[0] + '.lic', function, consttab)

if __name__=='__main__': main()
