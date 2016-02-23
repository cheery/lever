#!/usr/bin/env python
from compiler import bon, backend, grammarlang
import os
import sys

def main():
    assert len(sys.argv) == 3
    cb_path = sys.argv[1]
    src_path = sys.argv[2]
    debug = os.environ.get('VERBOSE', False)
    env = None
    root = parser.from_file(globals(), env, src_path, as_unicode=True)

    consttab = backend.ConstantTable()
    location_id = consttab.get(
        os.path.normpath(os.path.relpath(
            src_path, os.path.dirname(cb_path))).decode('utf-8'))
    functions = []
    ctx = Context(closures = [[root, None]])
    for body, scope in ctx.closures:
        ctx.scope = scope
        ctx.block = entry = backend.new_block()
        for cell in body:
            cell.visit(ctx)
        ctx.block.op(None, 'return', [ctx.block.op(None, 'getglob', [u"null"])])
        flags  = scope.flags  if scope else 0
        argc   = scope.argc   if scope else 0
        localv = scope.localv if scope else []
        functions.append(
            backend.dump(flags, argc, localv, entry,
                consttab, location_id, debug))
    with open(cb_path, 'wb') as fd:
        bon.dump(fd, {u'functions': functions, u'constants': consttab.constants})

class Context(object):
    def __init__(self, closures):
        self.closures = closures
        self.scope = None
        self.block = None
        self.loop_stack = []
        self.loop_continue = None
        self.loop_break = None

    def push_loop(self, cont, brek):
        self.loop_stack.append((self.loop_continue, self.loop_break))
        self.loop_continue = cont
        self.loop_break = brek

    def pop_loop(self):
        (self.loop_continue, self.loop_break) = self.loop_stack.pop()

class Scope(object):
    def __init__(self, parent, flags, argc, localv):
        self.parent = parent
        self.flags = flags
        self.argc = argc
        self.localv = localv

def post_function(env, loc, bindings, body):
    return Closure(loc, [b.value for b in bindings], body)

# TODO: 
# Eventually we actually also want to do scope dependence analysis, to
# lower some of the local variables into vreg variables.
class Cell(object):
    pass

class Closure(Cell):
    def __init__(self, loc, localv, body):
        self.loc = loc
        self.localv = localv 
        self.body = body

    def visit(self, context):
        handle = backend.Function(len(context.closures))
        context.closures.append([self.body, Scope(context.scope,
            0, len(self.localv), self.localv)])
        return context.block.op(self.loc, 'func', [handle])

def post_import(env, loc, names):
    import_fn = Getvar(loc, u"import")
    proc = []
    for name in names:
        cn = Code(loc, "constant", name.value)
        m = Code(loc, "call", import_fn, cn)
        proc.append(Setvar(loc, "auto", name.value, m))
    return Prog(proc)

def post_for(env, loc, bind, iterator, body):
    return ForBlock(loc, bind, iterator, body)

class ForBlock(Cell):
    def __init__(self, loc, bind, iterator, body):
        self.loc = loc
        self.bind = bind
        self.iterator = iterator
        self.body = body

    def visit(self, context):
        exit = backend.new_block()
        result = context.block.op(self.loc, 'getglob', [u"null"])
        iter = self.iterator.visit(context)
        iter = context.block.op(self.loc, 'iter', [iter])
        #context.block.op(self.loc, 'iterstop', [exit])
        repeat = label_this_point(self.loc, context.block)
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
        cont = label_this_point(self.loc, context.block)
        exit = backend.new_block()
        byes = backend.new_block()
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
 
def label_this_point(loc, block):
    if len(block) == 0:
        return block
    label = backend.new_block()
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
        exit = backend.new_block()
        other = backend.new_block()
        lhs = self.lhs.visit(context)
        context.block.op(self.loc, 'cond', [lhs, exit, other])
        context.block = other
        rhs = self.rhs.visit(context)
        other.op(self.loc, 'move', [lhs, rhs])
        other.op(self.loc, 'jump', [exit])
        context.block = exit
        return lhs

class And(Cell):
    def __init__(self, loc, lhs, rhs):
        self.loc = loc
        self.lhs = lhs
        self.rhs = rhs

    def visit(self, context):
        exit = backend.new_block()
        other = backend.new_block()
        lhs = self.lhs.visit(context)
        context.block.op(self.loc, 'cond', [lhs, other, exit])
        context.block = other
        rhs = self.rhs.visit(context)
        other.op(self.loc, 'move', [lhs, rhs])
        other.op(self.loc, 'jump', [exit])
        context.block = exit
        return lhs

class Cond(Cell):
    def __init__(self, cond, otherwise):
        self.cond = cond
        self.otherwise = otherwise

    def visit(self, context):
        exit = backend.new_block()
        result = context.block.op(None, 'getglob', [u'null'])
        branch = None
        for loc, cond, body in self.cond:
            if branch:
                context.block = bno = backend.new_block()
                blabel, bloc, bcond, byes = branch
                blabel.op(bloc, 'cond', [bcond, byes, bno])
            cond = cond.visit(context)
            label = context.block
            context.block = byes = backend.new_block()
            val = None
            for cell in body:
                val = cell.visit(context)
            if val is not None and val.has_result:
                context.block.op(loc, 'move', [result, val])
            context.block.op(loc, 'jump', [exit])
            branch = label, loc, cond, byes
        if self.otherwise:
            context.block = bno = backend.new_block()
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

def post_return(env, loc, expr):
    return Code(loc, "return", expr)
 
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
    return Setvar(loc, "local", name.value, statement)
 
def post_upvalue_assign(env, loc, name, statement):
    return Setvar(loc, "upvalue", name.value, statement)
 
def post_op_assign(env, loc, (getslot, setslot), op, statement):
    return setslot(Code(loc, 'call',
        Getvar(loc, op.value), getslot(), statement))

def post_lookup_slot(env, loc, name):
    def getslot():
        return Getvar(loc, name.value)
    def setslot(value):
        return Setvar(loc, "auto", name.value, value)
    return getslot, setslot

def post_attr_slot(env, loc, base, name):
    def getslot():
        return Code(loc, 'getattr', base, name.value)
    def setslot(stmt):
        return CodeM(loc, 'setattr', [base, name.value, stmt], [2, 0, 1])
    return getslot, setslot

def post_item_slot(env, loc, base, indexer):
    def getslot():
        return Code(loc, 'getitem', base, indexer)
    def setslot(value):
        print "toot"
        return CodeM(loc, 'setitem', [base, indexer, value], [2, 0, 1])
    return getslot, setslot
 
def post_in(env, loc, lhs, rhs):
    return CodeM(loc, 'contains', [rhs, lhs], [1, 0])

def post_not_in(env, loc, lhs, rhs):
    return CodeM(loc, 'not', CodeM(loc, 'contains', [rhs, lhs], [1, 0]))

def post_binary(env, loc, lhs, op, rhs):
    return CodeM(loc, 'call', [Getvar(loc, op.value), lhs, rhs], [1,2,0])

def post_prefix(env, loc, op, rhs):
    return CodeM(loc, 'call', [Getvar(loc, op.value + u"expr"), rhs], [1,0])

def post_call(env, loc, callee, args):
    return Code(loc, "call", callee, *args)

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

def post_list(env, loc, items):
    return Code(loc, "list", *items)

def post_dict(env, loc, pairs):
    return CodeGroup(loc, 'setitem',
        Code(loc, "call", Getvar(loc, u"dict")), pairs)

def post_empty_list(env, loc):
    return []

def post_pass(env, loc, val):
    return val

def post_first(env, loc, item):
    return [item]

def post_append(env, loc, seq, item):
    seq.append(item)
    return seq

def post_tuple(env, loc, *args):
    return args

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
                index = scope.localv.index(self.name)
                return context.block.op(self.loc, "getloc", [index])
            depth = 0
            while scope.parent:
                if self.name in scope.parent.localv:
                    index = scope.parent.localv.index(self.name)
                    return context.block.op(self.loc, "getupv", [depth, index])
                scope = scope.parent
                depth += 1
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
    if scope:
        if name in scope.localv and flavor != "upvalue":
            index = scope.localv.index(name)
            return context.block.op(loc, "setloc", [index, value])
        if flavor == "local":
            scope.localv.append(name)
            index = scope.localv.index(name)
            return context.block.op(loc, "setloc", [index, value])
        depth = 0
        while scope.parent:
            if name in scope.parent.localv:
                index = scope.parent.localv.index(name)
                return context.block.op(loc, "setupv", [depth, index, value])
            scope = scope.parent
            depth += 1
    return context.block.op(loc, "setglob", [name, value])

# TODO: LEVER_PATH most likely not set by lever itself. This will break.
lever_path = os.environ.get('LEVER_PATH', '')
parser = grammarlang.load({}, os.path.join(lever_path, 'lever.grammar'))

if __name__=='__main__': main()
