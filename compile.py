#!/usr/bin/env python
from compiler.program import ConstantTable, Function, Block, Constant, Op
from compiler import bon, grammarlang
import os
import sys

def main(debug=False):
    assert len(sys.argv) == 3
    cb_path = sys.argv[1]
    src_path = sys.argv[2]

    debug = os.environ.get('VERBOSE', debug)

    compile_file(cb_path, src_path, debug)

def compile_file(cb_path, src_path, debug):
    env = ASTScope(toplevel=True)
    consttab = ConstantTable()
    location_id = consttab.get(src_path.decode('utf-8'))
    body = parser.from_file(globals(), env, src_path)
    functions = ast_scope_close(env, body, consttab, [], location_id, toplevel=True)

    if debug:
        print 't'
        from evaluator import optable
        for func in functions:
            print func[:-2]
            block = func[-1]
            pc = 0
            while pc < len(block):
                print block
                opname, has_result, pattern, variadic = optable.dec[block[pc] >> 8]
                px = pc + 1
                pc = pc + 1 + (block[pc] & 255)
                args = block[px:pc]
                if has_result:
                    result = args.pop(0)
                    code = ' '.join(format_args(args, pattern, variadic, consttab.constants))
                    print "{:>2x}: {:2} = {:10} {}".format(px-1, result, opname, code)
                else:
                    code = ' '.join(format_args(args, pattern, variadic, consttab.constants))
                    print "{:>2x}:      {:10} {}".format(px-1, opname, code)
    with open(cb_path, 'wb') as fd:
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

def ast_scope_close(scope, body, consttab, functions, location_id, toplevel=False):
    localv = list(scope.defines)
    env = Scope(None, functions, localv)
    block = ScopeBlock(env)
    function = block.func_body(body, toplevel)
    return [func.dump(consttab, location_id) for func in functions]

class ASTScope(object):
    def __init__(self, toplevel=False):
        self.uses = set()
        self.defines = set()
        self.toplevel = toplevel

class Scope(object):
    def __init__(self, parent, functions, localv):
        self.blocks = []
        self.functions = functions
        self.localv = localv
        self.flags = 0x0
        self.argc = 0
        self.index = len(self.functions)
        self.functions.append(self)
        self.parent = parent

    def new_block(self):
        block = Block(0, [], set())
        self.blocks.append(block)
        return block

    def get_local(self, name):
        #if name not in self.localv:
        #    self.localv.append(name)
        return self.localv.index(name)

    def close(self):
        func = Function(self.index, self.flags, self.argc, self.localv, self.blocks)
        self.functions[self.index] = func
        return func

    def new_func(self, bindings, defines):
        scope = Scope(self, self.functions, [])
        scope.argc = len(bindings)
        for name in bindings:
            scope.localv.append(name.value.decode('utf-8'))
        scope.localv.extend(defines)
        return ScopeBlock(scope)

    def get_upvalue(self, name, depth=0):
        if self.parent is None:
            return None
        if name in self.parent.localv:
            return depth, self.parent.localv.index(name)
        else:
            return self.parent.get_upvalue(name, depth+1)

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

    def subblock(self, block=None):
        return ScopeBlock(self.scope, self, block)

    def op(self, loc, name, *args):
        op = Op(loc, name, args)
        self.block.append(op)
        return op

    def func_body(self, body, toplevel=False):
        lastv = None
        for stmt in body:
            lastv = stmt(self)
        if toplevel and lastv is not None:
            self.op(lastv.loc, 'return', lastv)
        else:
            lastv = self.op(None, 'getglob', Constant(u"null"))
            self.op(lastv.loc, 'return', lastv)
        return self.scope.close()

def post_import(env, loc, names):
    for name in names:
        env.defines.add(name.value)
    def build_import(block):
        import_fn = block.op(loc, 'getglob', Constant(u"import"))
        for name in names:
            name_const = block.op(loc, 'constant', Constant(name.value.decode('utf-8')))
            import_ = block.op(loc, 'call', import_fn, name_const)
            local = block.scope.get_local(name.value)
            local = block.op(loc, 'setloc', local, import_)
        return block.op(loc, 'getglob', Constant(u"null"))
    return build_import

def post_or(env, loc, a, b):
    def build_or(block):
        exit = block.scope.new_block()
        first = a(block)
        subblock = block.subblock()
        second = b(subblock)
        subblock.op(loc, 'move', first, second)
        subblock.op(loc, 'jump', exit)
        block.op(loc, 'cond', first, exit, subblock.first)
        block.block = exit
        return first
    return build_or

def post_and(env, loc, a, b):
    def build_and(block):
        exit = block.scope.new_block()
        first = a(block)
        subblock = block.subblock()
        second = b(subblock)
        subblock.op(loc, 'move', first, second)
        subblock.op(loc, 'jump', exit)
        block.op(loc, 'cond', first, subblock.first, exit)
        block.block = exit
        return first
    return build_and

def post_not(env, loc, expr):
    def build_not(block):
        return block.op(loc, 'not', expr(block))
    return build_not

def post_return(env, loc, expr):
    def build_return(block):
        value = expr(block)
        block.op(loc, 'return', value)
        return value
    return build_return

def pre_function(env, loc):
    return ASTScope()

def post_function(env, loc, bindings, body):
    def build_function(block):
        subblock = block.scope.new_func(bindings, env.defines)
        function = subblock.func_body(body)
        return block.op(loc, 'func', function)
    return build_function

def post_getattr(env, loc, base, name):
    def build_getattr(block):
        value = base(block)
        const = Constant(name.value.decode('utf-8'))
        return block.op(loc, 'getattr', value, const)
    return build_getattr

def post_setattr(env, loc, base, name, statement):
    def build_setattr(block):
        value = base(block)
        const = Constant(name.value.decode('utf-8'))
        return block.op(loc, 'setattr', value, const, statement(block))
    return build_setattr

def post_getitem(env, loc, base, indexer):
    def build_getitem(block):
        v0 = base(block)
        v1 = indexer(block)
        return block.op(loc, 'getitem', v0, v1)
    return build_getitem

def post_setitem(env, loc, base, indexer, statement):
    def build_getitem(block):
        v0 = base(block)
        v1 = indexer(block)
        v2 = statement(block)
        return block.op(loc, 'setitem', v0, v1, v2)
    return build_getitem

def post_local_assign(env, loc, name, statement):
    if env.toplevel:
        def build_toplevel_assign(block):
            return block.op(loc, 'setglob', Constant(name.value.decode('utf-8')), statement(block))
        return build_toplevel_assign
    env.defines.add(name.value)
    def build_local_assign(block):
        local = block.scope.get_local(name.value)
        local = block.op(loc, 'setloc', local, statement(block))
        return local
    return build_local_assign

def post_upvalue_assign(env, loc, name, binop, statement):
    def build_upvalue_assign(block):
        upv = block.scope.get_upvalue(name.value)
        if upv is not None:
            return block.op(loc, 'setupv', upv[0], upv[1], statement(block))
        else:
            return block.op(loc, 'setglob', Constant(name.value.decode('utf-8')), statement(block))
    return build_upvalue_assign

def post_op_assign(env, loc, slot, op, statement):
    def build_op_assign(block):
        getslot, setslot = slot(block)
        value = statement(block)
        o = block.op(loc, 'getglob', Constant(op.value.decode('utf-8')))
        return setslot(block.op(loc, 'call', o, getslot(), value))
    return build_op_assign

def post_lookup_slot(env, loc, name):
    def build_lookup_slot(block):
        if name in block.scope.localv:
            index = block.scope.localv.index(name)
            def getslot():
                return block.op(loc, 'getloc', index)
            def setslot(value):
                return block.op(loc, 'setloc', index, value)
            return getslot, setslot
        upv = block.scope.get_upvalue(name.value)
        def getslot():
            if upv is not None:
                return block.op(loc, 'getupv', *upv)
            else:
                return block.op(loc, 'getglob', Constant(name.value.decode('utf-8')))
        def setslot(value):
            if upv is not None:
                return block.op(loc, 'setupv', upv[0], upv[1], value)
            else:
                return block.op(loc, 'setglob', Constant(name.value.decode('utf-8')), value)
        return getslot, setslot
    return build_lookup_slot

def post_attr_slot(env, loc, base, name):
    def build_attr_slot(block):
        value = base(block)
        const = Constant(name.value.decode('utf-8'))
        def getslot():
            return block.op(loc, 'getattr', value, const)
        def setslot(stmt):
            return block.op(loc, 'setattr', value, const, stmt)
        return getslot, setslot
    return build_attr_slot

def post_item_slot(env, loc, base, indexer):
    def build_item_slot(block):
        v0 = base(block)
        v1 = indexer(block)
        def getslot():
            return block.op(loc, 'getitem', v0, v1)
        def setslot(value):
            return block.op(loc, 'setitem', v0, v1, value)
        return getslot, setslot
    return build_item_slot

def post_for(env, loc, bind, iterator, body):
    env.defines.add(bind.value)
    def build_for(block):
        exit = block.scope.new_block()
        result = block.op(loc, 'getglob', Constant(u'null'))
        iterat = block.op(loc, 'iter', iterator(block))
        block.op(loc, 'iterstop', exit)
        repeat = label_this_point(loc, block)
        index = block.scope.get_local(bind.value)
        block.op(loc, 'setloc', index, block.op(loc, 'next', iterat))
        subblock = block.subblock(block.block)
        block.block = exit
        compile_subblock(loc, subblock, body, repeat, result)
        return result
    return build_for

#    sub = env.subblock()
#    sub.loop_continue = sub.block
#    sub.loop_break = iterstop
#    sub.loop_iterstop = iterstop

def post_while(env, loc, cond, body):
    def build_while(block):
        resu = block.op(loc, 'getglob', Constant(u'null'))
        repe = label_this_point(loc, block)
        exit = block.scope.new_block()
        subblock = block.subblock()
        block.op(loc, 'cond', cond(block), subblock.first, exit)
        compile_subblock(loc, subblock, body, repe, resu)
        block.block = exit
        return resu
    return build_while

def label_this_point(loc, block):
    repe = block.scope.new_block()
    block.op(loc, 'jump', repe)
    block.block = repe
    return repe

def post_if(env, loc, cond, body, otherwise):
    def build_if(block):
        resu = block.op(loc, 'getglob', Constant(u'null'))
        exit = block.scope.new_block()
        subblock1 = block.subblock()
        subblock2 = block.subblock()
        b1 = compile_subblock(loc, subblock1, body, exit, resu)
        b2 = otherwise(subblock2, exit, resu)
        block.op(loc, 'cond', cond(block), b1, b2)
        block.block = exit
        return resu
    return build_if

def post_elif(env, loc, cond, body, otherwise):
    def build_elif(block, exit, resu):
        subblock1 = block.subblock()
        subblock2 = block.subblock()
        b1 = compile_subblock(loc, subblock1, body, exit, resu)
        b2 = otherwise(subblock2, exit, resu)
        block.op(loc, 'cond', cond(block), b1, b2)
        block.block = exit
        return block.first
    return build_elif

def post_else(env, loc, body):
    def build_else(block, exit, resu):
        return compile_subblock(loc, block, body, exit, resu)
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

def post_in(env, loc, lhs, rhs):
    def build_call(block):
        a = lhs(block)
        b = rhs(block)
        return block.op(loc, 'contains', b, a)
    return build_call

def post_not_in(env, loc, lhs, rhs):
    def build_call(block):
        a = lhs(block)
        b = rhs(block)
        return block.op(loc, 'not', block.op(loc, 'contains', b, a))
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
        upv = block.scope.get_upvalue(name)
        if upv is not None:
            return block.op(loc, 'getupv', *upv)
        else:
            return block.op(loc, 'getglob', Constant(name.decode('utf-8')))
    return build_lookup

def post_int(env, loc, num):
    def build_int(block):
        return block.op(loc, 'constant', Constant(int(num.value)))
    return build_int

def post_hex(env, loc, num):
    def build_hex(block):
        return block.op(loc, 'constant', Constant(int(num.value, 16)))
    return build_hex

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

def post_dict(env, loc, pairs):
    def build_dict(block):
        dict_ = block.op(loc, 'getglob', Constant(u"dict"))
        resu = block.op(loc, 'call', dict_)
        for key, value in pairs:
            v0 = key(block)
            v1 = value(block)
            block.op(loc, 'setitem', resu, v0, v1)
        return resu
    return build_dict

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

lever_path = os.environ.get('LEVER_PATH', '')
parser = grammarlang.load({}, os.path.join(lever_path, 'lever.grammar'))

if __name__=='__main__': main()
