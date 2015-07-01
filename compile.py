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
                    pc = pc + 1 + (block[pc] & 255)
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

    def new_block(self):
        block = Block(0, [], set())
        self.blocks.append(block)
        return block

    def get_local(self, name):
        if name not in self.localv:
            self.localv.append(name)
        return self.localv.index(name)

    def close(self):
        func = Function(self.index, self.flags, self.argc, self.localv, self.blocks)
        self.functions[self.index] = func
        return func

# Represents single 'block level' in the source code
# That means structured control flow changes the block pointer.
class ScopeBlock(object):
    def __init__(self, scope, parent=None, block=None):
        self.scope = scope
        self.block = scope.new_block() if block is None else block
        self.parent = parent
        self.first = self.block
        self.loop_continue = None if parent is None else parent.loop_continue 
        self.loop_break = None if parent is None else parent.loop_break
        self.loop_iterstop = None if parent is None else parent.loop_iterstop
        self.result = None

    def label(self, loc):
        if len(self.block) == 0:
            return self.block
        new_block = self.scope.new_block()
        self.op(loc, 'jump', new_block)
        self.block = new_block
        return self.block

    def subscope(self):
        return Scope(self, self.scope.functions)

    def subblock(self):
        return ScopeBlock(self.scope, self)

    def subblock_goto(self, env):
        return ScopeBlock(self.scope, self, self.label(env))

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
    index = env.scope.get_local(name)
    return env.op(loc, 'setloc', index, rhs)

def post_binding(env, loc, symbol):
    env.scope.localv.append(symbol.value)

def pre_subblock(env, loc):
    return env.subblock()

def post_subblock(env, loc, result):
    env.result = result
    return env

def pre_while(env, loc):
    result = env.op(loc, 'getglob', Constant('null'))
    env = env.subblock_goto(loc)
    env.loop_continue = env.block
    env.loop_break = env.parent.block = env.scope.new_block()
    env.result = result
    return env

def post_while(env, loc, cond, sub):
    env.op(loc, 'cond', cond, sub.first, env.loop_break)
    sub.op(loc, 'move', env.result, sub.result)
    sub.op(loc, 'jump', env.loop_continue)
    return env.result

def pre_for(env, loc):
    iterstop = env.scope.new_block()
    sub = env.subblock()
    sub.loop_continue = sub.block
    sub.loop_break = iterstop
    sub.loop_iterstop = iterstop
    return sub

def post_for(env, loc, bind, sub_result):
    parent = env.parent
    result = parent.op(loc, 'getglob', Constant('null'))
    parent.op(loc, 'iterstop', env.loop_iterstop)
    parent.op(loc, 'jump', env.loop_continue)
    env.op(loc, 'move', result, sub_result)
    env.op(loc, 'jump', env.loop_continue)
    parent.block = env.loop_iterstop
    if parent.loop_iterstop is not None:
        parent.op(loc, 'iterstop', parent.loop_iterstop)
    return result

def post_for_bind(env, loc, symbol, iterator):
    index = env.scope.get_local(symbol.value)
    value = env.op(loc, 'next', iterator)
    env.op(loc, 'setloc', index, value)

def pre_iter_statement(env, loc):
    return env.parent

def post_iter_statement(env, loc, statement):
    return env.op(loc, 'iter', statement)

def post_if(env, loc, cond, sub):
    exit = env.scope.new_block()
    result = env.op(loc, 'getglob', Constant('null'))
    env.op(loc, 'cond', cond, sub.first, exit)
    sub.op(loc, 'move', result, sub.result)
    sub.op(loc, 'jump', exit)
    env.block = exit
    return result

if __name__=='__main__': main(False)
