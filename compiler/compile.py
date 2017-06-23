#!/usr/bin/env python2
import bon, backend, grammarlang, grammar
import os
import sys

# Thanks to this, python-based-compiler doesn't need to have anything to
# do with the remaining runtime of lever.
lever_path = os.environ.get('LEVER_PATH', '')
parser = grammar.load(os.path.join(lever_path, 'lever-0.9.0.grammar'))

def main():
    assert len(sys.argv) == 3
    cb_path = sys.argv[1]
    src_path = sys.argv[2]
    compile_file(cb_path, src_path)

def compile_file(cb_path, src_path):
    debug = os.environ.get('VERBOSE', False)
    fn = lambda name, args, rest: globals()['post_'+name](None, rest[0], *args)
    root = parser.from_file(fn, [], src_path, as_unicode=True)

    consttab = backend.ConstantTable()
    location_id = 0
    functions = []

    root_scope = Scope(None, 0, 0, 0, [])
    ctx = Context(closures = [[root, root_scope, None]])
    for body, scope, origin in ctx.closures:
        ctx.scope = scope
        ctx.block = entry = ctx.new_block()
        for cell in body:
            cell.visit(ctx)
        ctx.block.op(None, 'return', [ctx.block.op(None, 'getglob', [u"null"])])
        flags  = scope.flags
        argc   = scope.argc
        topc   = scope.topc
        localv = scope.localv
        functions.append(
            backend.dump(flags, argc, topc, localv, entry,
                consttab, location_id, origin, debug))
    with open(cb_path, 'wb') as fd:
        bon.dump(fd, {
            u'functions': functions,
            u'constants': consttab.constants,
            u'sources': [
                os.path.normpath(os.path.relpath(src_path, os.path.dirname(cb_path))).decode('utf-8')],
            u'version': 0,
        })

class Context(object):
    def __init__(self, closures):
        self.closures = closures
        self.scope = None
        self.block = None
        self.loop_stack = []
        self.loop_continue = None
        self.loop_break = None
        self.exc = None

    def push_loop(self, cont, brek):
        self.loop_stack.append((self.loop_continue, self.loop_break))
        self.loop_continue = cont
        self.loop_break = brek

    def pop_loop(self):
        (self.loop_continue, self.loop_break) = self.loop_stack.pop()

    def new_block(self):
        return backend.new_block(self.exc)

class Scope(object):
    def __init__(self, parent, flags, argc, topc, localv):
        self.parent = parent
        self.flags = flags
        self.argc = argc
        self.topc = topc
        self.localv = localv
        self.depthc = 1

    # This ended up being not very clean.
    def object_scope(self, context, loc, parent, val):
        scope = ObjectScope(parent, self, [])
        index = len(self.localv)
        self.localv.append(scope)
        context.block.op(loc, "setloc", [index, val])
        return scope

    def getvar(self, context, loc, depth, name):
        if depth < 0:
            index = self.localv.index(name)
            return context.block.op(loc, "getloc", [index])
        else:
            index = self.localv.index(name)
            return context.block.op(loc, "getupv", [depth, index])

    def setvar(self, context, loc, depth, name, value):
        if depth < 0:
            index = self.localv.index(name)
            return context.block.op(loc, "setloc", [index, value])
        else:
            index = self.localv.index(name)
            return context.block.op(loc, "setupv", [depth, index, value])

class ObjectScope(object):
    def __init__(self, parent, scope, localv):
        self.parent = parent
        self.scope = scope
        self.localv = localv
        self.depthc = 0

    def object_scope(self, context, loc, parent, val):
        return self.parent.object_scope(context, loc, parent, val)

    def getvar(self, context, loc, depth, name):
        obj = self.scope.getvar(context, loc, depth, self)
        return context.block.op(loc, "getattr", [obj, name])

    def setvar(self, context, loc, depth, name, value):
        obj = self.scope.getvar(context, loc, depth, self)
        return context.block.op(loc, "setattr", [obj, name, value])

def post_function(env, loc, bindings, body):
    return Closure(loc, bindings, body)

# TODO: 
# Eventually we actually also want to do scope dependence analysis, to
# lower some of the local variables into vreg variables.
class Cell(object):
    pass

class Closure(Cell):
    def __init__(self, loc, bindings, body):
        self.loc = loc
        self.bindings = bindings 
        self.body = body

    def visit(self, context):
        flags = 0
        localv = []
        header = []
        variables, optionals, vararg = self.bindings
        argc = len(variables)
        topc = argc + len(optionals)
        for variable in variables:
            localv.append(variable.value)
        for variable, expr in (optionals if optionals else []):
            localv.append(variable.value)
            cond = Cond([[self.loc,
                Code(self.loc, "isnull", Getvar(self.loc, variable.value)), [
                    Setvar(self.loc, "local", variable.value, expr)
                ]]], None)
            header.append(cond)
        if vararg is not None:
            localv.append(vararg.value)
            flags |= 1
        handle = backend.Function(len(context.closures))

        if self.loc:
            origin = (0, self.loc[0].col, self.loc[0].lno,
                         self.loc[1].col, self.loc[1].col)
        else:
            origin = None
        context.closures.append([header + self.body,
            Scope(context.scope, flags, argc, topc, localv), origin])
        variables, optionals, vararg = self.bindings
        return context.block.op(self.loc, 'func', [handle])

def post_with_variadic(env, loc, bindings, vararg):
    bindings[2] = vararg
    return bindings

def post_only_variadic(env, loc, vararg):
    return [[], [], vararg]

def post_blank_bindings(env, loc):
    return [[], [], None]

def post_first_optional(env, loc, optional):
    return [[], [optional], None]

def post_optional(env, loc, name, expr):
    return name, expr

def post_mandatory(env, loc, mandatory):
    return [[mandatory], [], None]

def post_append_optional(env, loc, bindings, optional):
    bindings[1].append(optional)
    return bindings

def post_append_mandatory(env, loc, bindings, mandatory):
    bindings[0].append(mandatory)
    return bindings

def post_scopegrabber(env, loc, expr, block):
    return ScopeGrab(loc, expr, block)

def post_class(env, loc, (name, base), block=()):
    grabber = Code(loc, "call", Getvar(loc, u"object"))
    return Setvar(loc, "local", name,
        Code(loc, "call", Getvar(loc, u"class"),
            ScopeGrab(loc, grabber, block),
            base,
            Code(loc, "constant", name)))

def post_class_header(env, loc, name, base=None):
    if base is None:
        base = Getvar(loc, u"object") # May result in weird behavior at times.
    return name.value, base

class ScopeGrab(Cell):
    def __init__(self, loc, expr, body):
        self.loc = loc
        self.expr = expr
        self.body = body

    def visit(self, context):
        this = self.expr.visit(context)
        parent = context.scope
        context.scope = parent.object_scope(context, self.loc, parent, this)
        for expr in self.body:
            expr.visit(context)
        context.scope = parent
        return this

def post_import(env, loc, names):
    import_fn = Getvar(loc, u"import")
    proc = []
    for name in names:
        cn = Code(loc, "constant", name.value)
        m = Code(loc, "call", import_fn, cn)
        proc.append(Setvar(loc, "local", name.value, m))
    return Prog(proc)

def post_try(env, loc, body, excepts):
    return Try(loc, body, excepts)

def post_except(env, loc, expr, symbol, body):
    return [expr, symbol.value, body]

class Try(Cell):
    def __init__(self, loc, body, excepts):
        self.loc = loc
        self.body = body
        self.excepts = excepts

    def visit(self, context):
        result = context.block.op(self.loc, 'getglob', [u"null"])
        exit = context.new_block()
        context.exc = exc = backend.Exc(context.new_block(), context.exc)
        # populating try block
        try_block = context.new_block()
        context.block.op(self.loc, 'jump', [try_block])
        context.block = try_block
        val = None
        for expr in self.body:
            val = expr.visit(context)
        if val is not None and val.has_result:
            context.block.op(self.loc, 'move', [result, val])
        context.block.op(self.loc, 'jump', [exit])
        # populating exception block
        context.exc = exc.parent
        context.block = exc.block
        ins = context.block.op(self.loc, 'getglob', [u"isinstance"])
        for expr, name, body in self.excepts:
            this = context.new_block()
            next = context.new_block()
            which = expr.visit(context)
            cond = context.block.op(self.loc, 'call', [ins, exc, which])
            context.block.op(self.loc, 'cond', [cond, this, next])
            context.block = this
            setvar(context, self.loc, 'local', name, exc)
            val = None
            for expr in body:
                val = expr.visit(context)
            if val is not None and val.has_result:
                context.block.op(self.loc, 'move', [result, val])
            context.block.op(self.loc, 'jump', [exit])
            context.block = next
        context.block.op(self.loc, 'raise', [exc])
        # done
        context.block = exit
        return result

def post_for(env, loc, bind, iterator, body):
    return ForBlock(loc, bind, iterator, body)

class ForBlock(Cell):
    def __init__(self, loc, bind, iterator, body):
        self.loc = loc
        self.bind = bind
        self.iterator = iterator
        self.body = body

    def visit(self, context):
        exit = context.new_block()
        result = context.block.op(self.loc, 'getglob', [u"null"])
        iter = self.iterator.visit(context)
        iter = context.block.op(self.loc, 'iter', [iter])
        #context.block.op(self.loc, 'iterstop', [exit])
        repeat = label_this_point(self.loc, context, context.block)
        context.push_loop(repeat, exit)

        context.block = repeat
        value = context.block.op(self.loc, 'next', [iter, exit])
        setvar(context, self.loc, 'local', self.bind.value, value)
        val = None
        for expr in self.body:
            val = expr.visit(context)
        if val is not None and val.has_result:
            context.block.op(self.loc, 'move', [result, val])
        context.block.op(self.loc, 'jump', [repeat])
        
        context.block = exit
        context.pop_loop()
        #context.block.op(self.loc, 'iterstop', [iterstop])
        return result
 
def post_while(env, loc, cond, body):
    return WhileBlock(loc, cond, body)

class WhileBlock(Cell):
    def __init__(self, loc, cond, body):
        self.loc = loc
        self.cond = cond
        self.body = body

    def visit(self, context):
        result = context.block.op(self.loc, 'getglob', [u"null"])
        cont = label_this_point(self.loc, context, context.block)
        exit = context.new_block()
        byes = context.new_block()
        context.push_loop(cont, exit)

        context.block = cont
        cond = self.cond.visit(context)
        context.block.op(self.loc, 'cond', [cond, byes, exit])

        context.block = byes
        val = None
        for expr in self.body:
            val = expr.visit(context)
        if val is not None and val.has_result:
            context.block.op(self.loc, 'move', [result, val])
        context.block.op(self.loc, 'jump', [cont])

        context.block = exit
        context.pop_loop()
        return result
 
def label_this_point(loc, context, block):
    if len(block) == 0:
        return block
    label = context.new_block()
    block.op(loc, 'jump', [label])
    return label

def post_if(env, loc, cond, body, otherwise):
    otherwise[0].insert(0, [loc, cond, body])
    return Cond(*otherwise)

def post_elif(env, loc, cond, body, otherwise):
    otherwise[0].insert(0, [loc, cond, body])
    return otherwise

def post_else(env, loc, body):
    return ([], body)

def post_done(env, loc):
    return ([], None)

def post_assert(env, loc, cond, body=None):
    if isinstance(body, list):
        body = Prog(body)
    if body is None:
        body = Code(loc, "constant", u"")
    return Cond([[loc, Code(loc, "not", cond),
        [Code(loc, "assert", body)]]], None)

def post_or(env, loc, a, b):
    return Or(loc, a, b)

def post_and(env, loc, a, b):
    return And(loc, a, b)

class Or(Cell):
    def __init__(self, loc, lhs, rhs):
        self.loc = loc
        self.lhs = lhs
        self.rhs = rhs

    def visit(self, context):
        exit = context.new_block()
        other = context.new_block()
        lhs = self.lhs.visit(context)
        context.block.op(self.loc, 'cond', [lhs, exit, other])
        context.block = other
        rhs = self.rhs.visit(context)
        context.block.op(self.loc, 'move', [lhs, rhs])
        context.block.op(self.loc, 'jump', [exit])
        context.block = exit
        return lhs

class And(Cell):
    def __init__(self, loc, lhs, rhs):
        self.loc = loc
        self.lhs = lhs
        self.rhs = rhs

    def visit(self, context):
        exit = context.new_block()
        other = context.new_block()
        lhs = self.lhs.visit(context)
        context.block.op(self.loc, 'cond', [lhs, other, exit])
        context.block = other
        rhs = self.rhs.visit(context)
        context.block.op(self.loc, 'move', [lhs, rhs])
        context.block.op(self.loc, 'jump', [exit])
        context.block = exit
        return lhs

class Cond(Cell):
    def __init__(self, cond, otherwise):
        self.cond = cond
        self.otherwise = otherwise
        for line in cond:
            assert len(line) == 3, line

    def visit(self, context):
        exit = context.new_block()
        result = context.block.op(None, 'getglob', [u'null'])
        branch = None
        for loc, cond, body in self.cond:
            if branch:
                context.block = bno = context.new_block()
                blabel, bloc, bcond, byes = branch
                blabel.op(bloc, 'cond', [bcond, byes, bno])
            cond = cond.visit(context)
            label = context.block
            context.block = byes = context.new_block()
            val = None
            for cell in body:
                val = cell.visit(context)
            if val is not None and val.has_result:
                context.block.op(loc, 'move', [result, val])
            context.block.op(loc, 'jump', [exit])
            branch = label, loc, cond, byes
        if self.otherwise:
            context.block = bno = context.new_block()
            blabel, bloc, bcond, byes = branch
            blabel.op(bloc, 'cond', [bcond, byes, bno])
            val = None
            for cell in self.otherwise:
                val = cell.visit(context)
            if val is not None and val.has_result:
                context.block.op(bloc, 'move', [result, val])
            context.block.op(bloc, 'jump', [exit])
            label1 = context.block
        else:
            blabel, bloc, bcond, byes = branch
            blabel.op(bloc, 'cond', [bcond, byes, exit])
        context.block = exit
        return result

def post_return(env, loc, expr=None):
    if expr is None:
        expr = Code(loc, "getglob", u"null")
    return Code(loc, "return", expr)

def post_raise(env, loc, expr):
    return Code(loc, "raise", expr)

def post_break(env, loc):
    return Jumper(loc, lambda context: context.loop_break)

def post_continue(env, loc):
    return Jumper(loc, lambda context: context.loop_continue)

class Jumper(Cell):
    def __init__(self, loc, blockfn):
        self.loc = loc
        self.blockfn = blockfn

    def visit(self, context):
        block = self.blockfn(context)
        return context.block.op(self.loc, "jump", [block])

def post_not(env, loc, expr):
    return Code(loc, "not", expr)
 
def post_getattr(env, loc, base, name):
    return Code(loc, "getattr", base, name.value)
 
def post_setattr(env, loc, base, name, statement):
    return CodeM(loc, "setattr",
           [base, name.value, statement],
           [2, 0, 1])
 
def post_getitem(env, loc, base, indexer):
    return Code(loc, "getitem", base, indexer)
 
def post_setitem(env, loc, base, indexer, statement):
    return CodeM(loc, "setitem",
           [base, indexer, statement],
           [2, 0, 1])
 
def post_local_assign(env, loc, name, statement):
    return Setvar(loc, "local", name, statement)

def post_str_join(env, loc, *names):
    return u"".join(n.value for n in names)
 
def post_upvalue_assign(env, loc, name, statement):
    return Setvar(loc, "upvalue", name.value, statement)
 
def post_op_assign(env, loc, (base, getslot, setslot), op, statement):
    bind = Let(base)
    return bind(setslot(bind, Code(loc, 'call',
        Getvar(loc, op.value), getslot(bind), statement)))

def post_lookup_slot(env, loc, name):
    def getslot(base):
        return Getvar(loc, name.value)
    def setslot(base, value):
        return Setvar(loc, "auto", name.value, value)
    return None, getslot, setslot

def post_attr_slot(env, loc, base, name):
    def getslot(base):
        return Code(loc, 'getattr', base, name.value)
    def setslot(base, stmt):
        return CodeM(loc, 'setattr', [base, name.value, stmt], [2, 0, 1])
    return base, getslot, setslot

def post_item_slot(env, loc, base, indexer):
    def getslot(base):
        return Code(loc, 'getitem', base, indexer)
    def setslot(base, value):
        return CodeM(loc, 'setitem', [base, indexer, value], [2, 0, 1])
    return base, getslot, setslot
 
def post_in(env, loc, lhs, rhs):
    return CodeM(loc, 'contains', [rhs, lhs], [1, 0])

def post_not_in(env, loc, lhs, rhs):
    return Code(loc, 'not', CodeM(loc, 'contains', [rhs, lhs], [1, 0]))

def post_binary(env, loc, lhs, op, rhs):
    return CodeM(loc, 'call', [Getvar(loc, op.value), lhs, rhs], [1,2,0])

def post_slice_incr(env, loc, start, stop, step=None):
    if start is None:
        start = Code(loc, "getglob", u"null")
    if stop is None:
        stop = Code(loc, "getglob", u"null")
    if step is None:
        step = Code(loc, "constant", 1)
    return Code(loc, "call", Code(loc, "getglob", u"slice"), start, stop, step)

def post_slice_decr(env, loc, start, stop, step=None):
    if start is None:
        start = Code(loc, "getglob", u"null")
    if stop is None:
        stop = Code(loc, "getglob", u"null")
    if step is None:
        step = Code(loc, "constant", -1)
    else:
        step = Code(loc, "call", Getvar(u"-expr"), step)
    return Code(loc, "call", Code(loc, "getglob", u"slice"), start, stop, step)

def post_prefix(env, loc, op, rhs):
    return CodeM(loc, 'call', [Getvar(loc, op.value + u"expr"), rhs], [1,0])

def post_call(env, loc, callee, args):
    return Code(loc, "call", callee, *args)

def post_callv(env, loc, callee, args):
    return Code(loc, "callv", callee, *args)

def post_lookup(env, loc, symbol):
    return Getvar(loc, symbol.value)

def post_int(env, loc, num):
    return Code(loc, "constant", int(num.value))

def post_hex(env, loc, num):
    return Code(loc, "constant", int(num.value, 16))

def post_float(env, loc, num):
    return Code(loc, "constant", float(num.value))

def post_string(env, loc, string):
    return Code(loc, "constant", string.value)

def post_implicit_string_pair(env, loc, string, expr):
    return (Code(loc, "constant", string.value), expr)

def post_list(env, loc, items):
    return Code(loc, "list", *items)

def post_dict(env, loc, pairs):
    return CodeGroup(loc, 'setitem',
        Code(loc, "call", Getvar(loc, u"dict")), pairs)

def post_empty_list(env, loc):
    return []

def post_pass(env, loc, val):
    return val

def post_nil(env, loc):
    return None

def post_first(env, loc, item):
    return [item]

def post_append(env, loc, seq, item):
    seq.append(item)
    return seq

def post_tuple(env, loc, *args):
    return args

def post_tuple3(env, loc, arg0=None, arg1=None, arg2=None):
    return (arg0, arg1, arg2)

class Code(Cell):
    def __init__(self, loc, name, *args):
        self.loc = loc
        self.name = name
        self.args = args
        for arg in args:
            assert not isinstance(arg, list)

    def visit(self, context):
        args = []
        for arg in self.args:
            if isinstance(arg, Cell):
                arg = arg.visit(context)
            args.append(arg)
        return context.block.op(self.loc, self.name, args)

class CodeM(Cell):
    def __init__(self, loc, name, args, order):
        self.loc = loc
        self.name = name
        self.args = args
        self.order = order

    def visit(self, context):
        args = [None for arg in self.args]
        for i in self.order:
            if isinstance(self.args[i], Cell):
                args[i] = self.args[i].visit(context)
            else:
                args[i] = self.args[i]
        return context.block.op(self.loc, self.name, args)

# Actually apply the same trick to import(), maybe it becomes to CodeGroup ?
# One slightly tricky.
class CodeGroup(Cell):
    def __init__(self, loc, name, prefix, groups):
        self.loc = loc
        self.name = name
        self.prefix = prefix
        self.groups = groups

    def visit(self, context):
        prefix = self.prefix.visit(context)
        for seq in self.groups:
            argv = [prefix]
            argv.extend(item.visit(context) for item in seq)
            context.block.op(self.loc, self.name, argv)
        return prefix

class Prog(Cell):
    def __init__(self, exprs):
        self.exprs = exprs

    def visit(self, context):
        val = None
        for expr in self.exprs:
            val = expr.visit(context)
        assert val is not None
        return val

class Getvar(Cell):
    def __init__(self, loc, name):
        self.loc = loc
        self.name = name
        assert isinstance(name, unicode)

    def visit(self, context):
        scope = context.scope
        if scope:
            if self.name in scope.localv:
                return scope.getvar(context, self.loc, -1, self.name)
            depth = scope.depthc - 1
            while scope.parent:
                if self.name in scope.parent.localv:
                    return scope.parent.getvar(context, self.loc, depth, self.name)
                depth += scope.parent.depthc
                scope = scope.parent
        return context.block.op(self.loc, "getglob", [self.name])

class Setvar(Cell):
    def __init__(self, loc, flavor, name, value):
        self.loc = loc
        self.flavor = flavor # local, auto, upvalue
        self.name = name
        self.value = value

    def visit(self, context):
        value = self.value.visit(context)
        return setvar(context, self.loc, self.flavor, self.name, value)

def setvar(context, loc, flavor, name, value):
    scope = context.scope
    # The setvar doesn't write into the rootscope.
    if scope.parent:
        if name in scope.localv and flavor != "upvalue":
            return scope.setvar(context, loc, -1, name, value)
        if flavor == "local":
            scope.localv.append(name)
            return scope.setvar(context, loc, -1, name, value)
        depth = scope.depthc - 1
        while scope.parent.parent:
            if name in scope.parent.localv:
                return scope.parent.setvar(context, loc, depth, name, value)
            depth += scope.depthc
            scope = scope.parent
    return context.block.op(loc, "setglob", [name, value])

class Let(Cell):
    def __init__(self, value):
        self.value = value
        self.reg = None
    
    def __call__(self, body):
        return LetBody(self, body)

    def visit(self, context):
        assert self.reg is not None
        return self.reg
    
class LetBody(Cell):
    def __init__(self, binding, body):
        self.binding = binding
        self.body = body

    def visit(self, context):
        if self.binding.value is not None:
            self.binding.reg = self.binding.value.visit(context)
        result = self.body.visit(context)
        self.binding.reg = None
        return result

if __name__=='__main__': main()
