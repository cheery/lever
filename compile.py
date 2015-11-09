from compiler.program import ConstantTable, Function, Block, Constant, Op
from compiler import bon, grammarlang
import os
import sys

def main(debug=False):
    for name in sys.argv[1:]:
        compile_file(name, debug)

def compile_file(name, debug=False):
    env = ASTScope()
    body = parser.from_file(globals(), env, name)
    builder = env.close(body, toplevel=True)

    consttab = ConstantTable()
    functions = builder(consttab, functions=[])

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
    with open(os.path.splitext(name)[0] + '.lic', 'wb') as fd:
        bon.dump(fd, {
            u'functions': functions,
            u'constants': list(consttab.constants),
        })

def format_args(args, pattern, variadic, constants):
    pattern = pattern + [variadic]*(len(args) - len(pattern))
    for arg, pat in zip(args, pattern):
        if pat == 'vreg':
            yield "{:}".format(arg)
        elif pat in ('constant', 'string'):
            yield "{!r}({})".format(constants[arg], arg)
        else:
            yield "{}({:x})".format(pat, arg)

class ASTScope(object):
    def __init__(self):
        self.uses = set()
        self.defines = set()

    def close(self, body, toplevel=False):
        def build_function(consttab, functions):
            localv = list(self.defines)
            env = Scope(None, functions, localv)
            block = ScopeBlock(env)
            lastv = None
            for stmt in body:
                lastv = stmt(block)
            if toplevel and lastv is not None:
                block.op(lastv.loc, 'return', lastv)
            else:
                lastv = block.op(None, 'getglob', Constant(u"null"))
                block.op(lastv.loc, 'return', lastv)
            function = env.close()
            return [func.dump(consttab) for func in functions]
        return build_function

class Scope(object):
    def __init__(self, parent_block, functions, localv):
        self.blocks = []
        self.functions = functions
        self.localv = localv
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

#    def subscope(self):
#        return Scope(self, self.scope.functions)

    def subblock(self):
        return ScopeBlock(self.scope, self)

    def op(self, loc, name, *args):
        op = Op(loc, name, args)
        self.block.append(op)
        return op

parser = grammarlang.load({}, 'lever.grammar')

def post_return(env, loc, expr):
    def build_return(block):
        value = expr(block)
        block.op(loc, 'return', value)
        return value
    return build_return

#def pre_function(env, loc):
#    return ScopeBlock(env.subscope())
#
#def post_function(env, loc, bindings):
#    env.scope.argc = len(bindings)
#    parent = env.scope.parent_block
#    return parent.op(loc, 'func', env.scope.close())
#
#def post_binding(env, loc, symbol):
#    env.scope.localv.append(symbol.value)
#
#def pre_subblock(env, loc):
#    return env.subblock()
#
#def post_subblock(env, loc, result):
#    env.result = result
#    return env
#
#def pre_while(env, loc):
#    result = env.op(loc, 'getglob', Constant(u'null'))
#    env = env.subblock_goto(loc)
#    env.loop_continue = env.block
#    env.loop_break = env.parent.block = env.scope.new_block()
#    env.result = result
#    return env
#
#def post_while(env, loc, cond, sub):
#    env.op(loc, 'cond', cond, sub.first, env.loop_break)
#    sub.op(loc, 'move', env.result, sub.result)
#    sub.op(loc, 'jump', env.loop_continue)
#    return env.result
#
#def pre_for(env, loc):
#    iterstop = env.scope.new_block()
#    sub = env.subblock()
#    sub.loop_continue = sub.block
#    sub.loop_break = iterstop
#    sub.loop_iterstop = iterstop
#    return sub
#
#def post_for(env, loc, bind, sub_result):
#    parent = env.parent
#    result = parent.op(loc, 'getglob', Constant(u'null'))
#    parent.op(loc, 'iterstop', env.loop_iterstop)
#    parent.op(loc, 'jump', env.loop_continue)
#    env.op(loc, 'move', result, sub_result)
#    env.op(loc, 'jump', env.loop_continue)
#    parent.block = env.loop_iterstop
#    if parent.loop_iterstop is not None:
#        parent.op(loc, 'iterstop', parent.loop_iterstop)
#    return result
#
#def post_for_bind(env, loc, symbol, iterator):
#    index = env.scope.get_local(symbol.value)
#    value = env.op(loc, 'next', iterator)
#    env.op(loc, 'setloc', index, value)
#
#def pre_iter_statement(env, loc):
#    return env.parent
#
#def post_iter_statement(env, loc, statement):
#    return env.op(loc, 'iter', statement)

def post_getattr(env, loc, base, name):
    def build_getattr(block):
        value = base(block)
        const = Constant(name.value.decode('utf-8'))
        return block.op(loc, 'getattr', value, const)
    return build_getattr

def post_getitem(env, loc, base, indexer):
    def build_getitem(block):
        v0 = base(block)
        v1 = indexer(block)
        return block.op(loc, 'getitem', v0, v1)
    return build_getitem

def post_local_assign(env, loc, name, statement):
    def build_local_assign(block):
        local = block.scope.get_local(name.value.decode('utf-8'))
        local = block.op(loc, 'setloc', local, statement(block))
        return local
    return build_local_assign

def post_while(env, loc, cond, body):
    def build_while(block):
        resu = block.op(loc, 'getglob', Constant(u'null'))
        repe = block.scope.new_block()
        block.op(loc, 'jump', repe)
        block.block = repe
        exit = block.scope.new_block()
        subblock = block.subblock()
        block.op(loc, 'cond', cond(block), subblock.first, exit)
        compile_subblock(loc, subblock, body, repe, resu)
        block.block = exit
        return resu
    return build_while


def post_if(env, loc, cond, body, otherwise):
    def build_if(block):
        resu = block.op(loc, 'getglob', Constant(u'null'))
        exit = block.scope.new_block()
        othw = otherwise(block, exit, resu)
        subblock = block.subblock()
        block.op(loc, 'cond', cond(block), subblock.first, othw)
        compile_subblock(loc, subblock, body, exit, resu)
        block.block = exit
        return resu
    return build_if

def post_elif(env, loc, cond, body, otherwise):
    def build_elif(block, exit, resu):
        othw = otherwise(block, exit, resu)
        subblock = block.subblock()
        block.op(loc, 'cond', cond(block), subblock.first, othw)
        return compile_subblock(loc, subblock, body, exit, resu)
    return build_elif

def post_else(env, loc, body):
    def build_else(block, exit, resu):
        subblock = block.subblock()
        return compile_subblock(loc, subblock, body, exit, resu)
    return build_else

def post_done(env, loc):
    def build_done(block, exit, resu):
        return exit
    return build_done

def compile_subblock(loc, subblock, body, exit, resu):
    retv = resu
    for stmt in body:
        retv = stmt(subblock)
    subblock.op(loc, 'move', resu, retv)
    subblock.op(loc, 'jump', exit)
    return subblock.first

def post_call(env, loc, callee, args):
    def build_call(block):
        a = [arg(block) for arg in args]
        c = callee(block)
        return block.op(loc, 'call', c, *a)
    return build_call

def post_binary(env, loc, lhs, op, rhs):
    def build_call(block):
        a = lhs(block)
        b = rhs(block)
        c = block.op(loc, 'getglob', Constant(op.value.decode('utf-8')))
        return block.op(loc, 'call', c, a, b)
    return build_call

def post_prefix(env, loc, op, rhs):
    def build_call(block):
        a = rhs(block)
        c = block.op(loc, 'getglob', Constant(op.value + u"expr"))
        return block.op(loc, 'call', c, a)
    return build_call

def post_lookup(env, loc, symbol):
    name = symbol.value
    env.uses.add(name)
    def build_lookup(block):
        if name in block.scope.localv:
            index = block.scope.localv.index(name)
            return block.op(loc, 'getloc', index)
        # XXX: add upscope lookup here
        else:
            return block.op(loc, 'getglob', Constant(name.decode('utf-8')))
    return build_lookup

def post_int(env, loc, num):
    def build_int(block):
        return block.op(loc, 'constant', Constant(int(num.value)))
    return build_int

def post_float(env, loc, num):
    def build_float(block):
        return block.op(loc, 'constant', Constant(float(num.value)))
    return build_float

def post_string(env, loc, string):
    def build_string(block):
        return block.op(loc, 'constant', Constant(string.value.decode('utf-8')))
    return build_string

def post_list(env, loc, items):
    def build_list(block):
        vals = [item(block) for item in items]
        return block.op(loc, 'list', *vals)
    return build_list

def post_empty_list(env, loc):
    return []

def post_first(env, loc, item):
    return [item]

def post_append(env, loc, seq, item):
    seq.append(item)
    return seq

def post_pass(env, loc, val):
    return val

def post_tuple(env, loc, *args):
    return args


if __name__=='__main__': main()
