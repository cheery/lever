from objects import common
from objects import *
from context import construct_coeffect

def read_script(code, preset, env):
    module = Module()
    for key, value in preset.items():
        module.assign(key, value)
    code = as_dict(code)
    sources = as_list(attr(code, u"sources"))
    return Closure(code, module, env, [], sources), module

@builtin()
def w_inspect(closure):
    closure = cast(closure, Closure)
    frame = []
    for cell in closure.frame:
        frame.append(cell.val)
    return construct_record([
        (u"module", False, closure.module),
        (u"env", False, List(list(closure.env))),
        (u"frame", False, List(frame)),
        (u"sources", False, List(list(closure.sources))),
        (u"cellvars", False, List(closure.cellvars)),
        (u"localvars", False, List(closure.localvars)),
        (u"args", False, List(closure.args)),
        (u"body", False, List(closure.body)),
        (u"loc", False, List(closure.loc)) ])

# Closures have similar challenges as what builtin functions
# have.
class ClosureInterface(FunctionInterface):
    def method(self, op):
        if op is op_call:
            return w_call_closure
        return FunctionInterface.method(self, op)

attr_method(ClosureInterface.interface,
    u"params")(common.FunctionInterface_params)
method(ClosureInterface.interface,
    op_eq)(common.FunctionInterface_eq)
method(ClosureInterface.interface,
    op_hash)(common.FunctionInterface_hash)

closure_interfaces = FunctionMemo(ClosureInterface)

class Closure(Object):
    interface = None
    def __init__(self, code, module, env, frame, sources):
        self.module = module
        self.env = env
        self.frame = frame
        self.sources = sources

        # cell and local variables have 'defs' -field that
        # has count of how many assignments there are in the
        # program for that variable.
        self.cellvars = as_list(attr(code, u"cellvars"))
        self.localvars = as_list(attr(code, u"localvars"))

        if as_string(attr(code, u"type")) == u"script":
            self.args = []
            self.body = as_list(attr(code, u"body"))
            self.loc  = [fresh_integer(0)] * 5
        elif as_string(attr(code, u"type")) == u"closure":
            self.args = as_list(attr(code, u"args"))
            self.body = as_list(attr(code, u"body"))
            self.loc  = as_list(attr(code, u"loc"))
        else:
            raise error(e_EvalError())

        self.closure_face = closure_interfaces.get(
            len(self.args), False, 0)
        assert isinstance(self.closure_face, ClosureInterface)

    def face(self):
        return self.closure_face

# json-as-bytecode is supposed to be a temporary measure,
# but who knows how long we will have it. It already shows
# that it was the right choice at the beginning.
def call_closure(closure, args):
    closure = cast(closure, Closure)
    if len(closure.args) != len(args):
        tb = error(e_TypeError())
        tb.trace.append((closure.loc, closure.sources))
        raise tb
    cellvars = closure.frame + [
        Cell()
        for _ in range(len(closure.frame), len(closure.cellvars))]
    localvars = [null
        for _ in range(len(closure.localvars))]
    ctx = EvaluationContext(
        localvars, cellvars,
        closure.module, closure.env, closure.sources)
    for i in range(len(args)):
        arg = as_dict(closure.args[i])
        slot  = as_dict(attr(arg, u"slot"))
        eval_slot(ctx, slot).store(ctx, args[i])
    stack = [(closure.body, 0, None)]
    try:
        eval_program(ctx, stack)
    except Return as r:
        return r.value
    except Yield:
        raise error(e_TypeError())
    finally:
        while len(stack) > 0:
            stack.pop()
    return null

w_call_closure = python_bridge(call_closure, vari=True)

# Generators are incredibly much more simpler than Closures
# because we do not give them an argument list.
def fresh_generator(code, module, env, frame, sources):
    cellvars = as_list(attr(code, u"cellvars"))
    localvars = as_list(attr(code, u"localvars"))
    body = as_list(attr(code, u"body"))
    cellvars = frame + [Cell()
        for _ in range(len(frame), len(cellvars))]
    localvars = [null for _ in range(len(localvars))]
    stack = [(body, 0, None)]
    return Generator(GeneratorTip(module, env, sources,
        cellvars, localvars, stack))

class GeneratorTip:
    def __init__(self, module, env, sources, cellvars, localvars, stack):
        self.module = module
        self.env = env
        self.sources = sources
        self.cellvars = cellvars
        self.localvars = localvars
        self.stack = stack

    def step(self):
        if len(self.stack) == 0:
            raise StopIteration()
        ctx = EvaluationContext(
            self.localvars, self.cellvars,
            self.module, self.env, self.sources,
            is_generator=True)
        try:
            eval_program(ctx, self.stack)
        except Yield as y:
            return y.value
        except Return:
            raise error(e_TypeError())
        raise StopIteration()

class Generator(Iterator):
    interface = Iterator.interface
    def __init__(self, tip):
        self.tip = tip
        self.current = None
        self.tail = None

    def next(self):
        if self.current is None:
            self.current = self.tip.step()
            self.tail = Generator(self.tip)
        return self.current, self.tail

# TODO: add a flag telling whether it's function or
# generator we are running. allow/disallow return/yield.
class EvaluationContext:
    def __init__(self, localvars, cellvars, module, env, sources,
                 is_generator=False):
        self.localvars = localvars
        self.cellvars = cellvars
        self.module = module
        self.env = env
        self.sources = sources
        self.is_generator = is_generator


# The evaluator is layered and now really distinguishes
# between statements and functions. That makes it easier to
# implement but also, I never really used the 'if' as
# an expression in the previous interpreters for
# readability reasons.

def eval_program(ctx, stack):
    while len(stack) > 0:
        body, start, mod = stack.pop()
        try:
            eval_block(ctx, body, start, mod, stack)
        except Traceback as tb:
            while not isinstance(mod, Except):
                if len(stack) == 0:
                    raise
                body, start, mod = stack.pop()
            for row in mod.excepts:
                row = as_dict(row)
                exc = eval_expr(ctx, as_dict(attr(row, u"exc")))
                if tb.error.face() is exc:
                    slot = row.get(String(u"slot"), None)
                    if slot is not None:
                        eval_slot(ctx, as_dict(slot)).store(ctx, tb.error)
                    body = as_list(attr(row, u"body"))
                    stack.append((body, 0, None))
                    break
            else:
                raise

class Return(Exception):
    def __init__(self, value):
        self.value = value

class Yield(Exception):
    def __init__(self, value):
        self.value = value

def eval_block(ctx, body, start, mod, stack):
    for i in range(start, len(body)):
        stmt = as_dict(body[i])
        tp = as_string(attr(stmt, u"type"))
        if tp == u"return" and not ctx.is_generator:
            expr = as_dict(attr(stmt, u"value"))
            raise Return(eval_expr(ctx, expr))
        elif tp == u"yield" and ctx.is_generator:
            expr = as_dict(attr(stmt, u"value"))
            stack.append((body, i+1, mod))
            raise Yield(eval_expr(ctx, expr))
        elif tp == u"break":
            while not isinstance(mod, Loop):
                if len(stack) == 0:
                    raise error(e_EvalError())
                body, start, mod = stack.pop()
            mod = None
            break
        elif tp == u"continue":
            while not isinstance(mod, Loop):
                if len(stack) == 0:
                    raise error(e_EvalError())
                body, start, mod = stack.pop()
            break
        elif tp == u"repeat":
            fresh = as_list(attr(stmt, u"fresh"))
            heads = as_list(attr(stmt, u"heads"))
            stack.append((body, i+1, mod))
            body = as_list(attr(stmt, u"body"))
            mod  = eval_loop_header(ctx, heads, fresh)
            break
        elif tp == u"cond":
            cond = as_dict(attr(stmt, u"cond"))
            cond = eval_expr(ctx, cond)
            if convert(cond, Bool) is true:
                stack.append((body, i+1, mod))
                body = as_list(attr(stmt, u"tbody"))
                stack.append((body, 0, None))
            else:
                stack.append((body, i+1, mod))
                body = as_list(attr(stmt, u"fbody"))
                stack.append((body, 0, None))
            mod  = None
            break
        elif tp == u"case":
            value = eval_expr(ctx, as_dict(attr(stmt, u"value")))
            cases = as_list(attr(stmt, u"cases"))
            default = as_list(attr(stmt, u"default"))
            body = eval_case(ctx, value, cases, default)
            stack.append((body, 0, None))
            mod = None
            break
        elif tp == u"datatype":
            varc = len(as_list(attr(stmt, u"vars")))
            dt = new_datatype(varc)
            eval_slot(ctx, as_dict(attr(stmt, u"slot"))).store(ctx, dt)
            for row in as_list(attr(stmt, u"rows")):
                row = as_list(row)
                if len(row) != 2:
                    raise error(e_EvalError())
                row_slot = as_dict(row[0])
                row_params = as_list(row[1])
                params = []
                labels = {}
                for i, param in enumerate(row_params):
                    param = as_dict(param)
                    ptp = as_string(attr(param, u"type"))
                    if ptp == u"label":
                        labels[as_string(attr(param, u"name"))] = i
                        params.append(eval_expr(ctx,
                            as_dict(attr(param, u"value"))))
                    elif ptp == u"no_label":
                        params.append(eval_expr(ctx,
                            as_dict(attr(param, u"value"))))
                    else:
                        raise error(e_EvalError())
                if len(params) == 0:
                    row = new_constant(dt)
                else:
                    row = new_constructor(dt, params, labels)
                eval_slot(ctx, row_slot).store(ctx, row)
            for decl in as_list(attr(stmt, u"decls")):
                decl = as_dict(decl)
                eval_decl(ctx, dt, decl)
            dt.close()
        elif tp == u"operator":
            slot = eval_slot(ctx, as_dict(attr(stmt, u"slot")))
            selector = eval_expr(ctx, as_dict(attr(stmt, u"selector")))
            it = cast(call(op_iter, [selector]), Iterator)
            selectors = []
            while True:
                try:
                    x, it = it.next()
                    selectors.append(cast(x, Integer).toint())
                except StopIteration:
                    break
            op = Operator(selectors)
            for decl in as_list(attr(stmt, u"decls")):
                decl = as_dict(decl)
                dtp = as_string(attr(decl, u"type"))
                if dtp == u"method":
                    face = eval_expr(ctx, as_dict(attr(decl, u"op")))
                    value = eval_expr(ctx, as_dict(attr(decl, u"value")))
                    op.methods[cast(face, Interface)] = value
                elif dtp == u"default_method":
                    op.default = eval_expr(ctx, as_dict(attr(decl, u"value")))
                else:
                    raise error(e_EvalError())
            slot.store(ctx, op)
        elif tp == u"except":
            stack.append((body, i+1, mod))
            body = as_list(attr(stmt, u"body"))
            excepts = as_list(attr(stmt, u"excepts"))
            # exc, slot, body
            stack.append((body, 0, Except(excepts)))
            mod = None
            break
        else:
            eval_expr(ctx, stmt)
    if isinstance(mod, Loop):
        count = len(mod.heads)
        k, restart = mod.index, (mod.index == 0)
        k -= int(not restart)
        while 0 <= k < count:
            if restart:
                restart = mod.heads[k].restart(ctx)
            else:
                restart = mod.heads[k].step(ctx)
            if restart:
                k += 1
            else:
                k -= 1
        if restart:
            mod.index = k
            for index in mod.fresh:
                index = as_integer(index)
                ctx.cellvars[index] = Cell()
            stack.append((body, 0, mod))

# Loops were finicky to implement due to the multiple heads
# that I allow. Each loop may have multiple heads that have
# to start and stop in correct order.
def eval_loop_header(ctx, input_heads, fresh):
    heads = []
    for head in input_heads:
        head = as_dict(head)
        tp = as_string(attr(head, u"type"))
        if tp == u"for":
            slot = as_dict(attr(head, u"slot"))
            value = as_dict(attr(head, u"value"))
            heads.append(ForLoop(slot, value))
        if tp == u"while":
            cond = as_dict(attr(head, u"cond"))
            heads.append(WhileLoop(cond))
        if tp == u"if":
            cond = as_dict(attr(head, u"cond"))
            heads.append(IfLoop(cond))
    return Loop(fresh, heads)

class StatementMod:
    pass

class Except(StatementMod):
    def __init__(self, excepts):
        self.excepts = excepts

class Loop(StatementMod):
    def __init__(self, fresh, heads):
        self.fresh = fresh
        self.heads = heads
        self.index = 0

class LoopHead:
    def restart(self, ctx):
        return self.step(ctx)

    def step(self, ctx):
        return False

class ForLoop(LoopHead):
    def __init__(self, slot, value):
        self.slot = slot
        self.iterator = None
        self.value = value

    def restart(self, ctx):
        it = call(op_iter, [eval_expr(ctx, self.value)])
        self.iterator = cast(it, Iterator)
        return self.step(ctx)

    def step(self, ctx):
        try:
            value, self.iterator = self.iterator.next()
        except StopIteration:
            return False
        else:
            eval_slot(ctx, self.slot).store(ctx, value)
            return True

class WhileLoop(LoopHead):
    def __init__(self, cond):
        self.cond = cond

    def step(self, ctx):
        if convert(eval_expr(ctx, self.cond), Bool) is true:
            return True
        else:
            return False

class IfLoop(LoopHead):
    def __init__(self, cond):
        self.cond = cond

    def restart(self, ctx):
        if convert(eval_expr(ctx, self.cond), Bool) is true:
            return True
        else:
            return False

    def step(self, ctx):
        return False

def eval_case(ctx, value, cases, default):
    for case in cases:
        case = as_dict(case)
        tp = as_string(attr(case, u"type"))
        if tp == u"constant":
            constant = eval_expr(ctx, as_dict(attr(case, u"value")))
            if convert(call(op_eq, [value, constant]), Bool) is true:
                return as_list(attr(case, u"body"))
        elif tp == u"pattern":
            pattern = eval_expr(ctx, as_dict(attr(case, u"pattern")))
            tup = cast(call(op_pattern, [pattern]), Tuple).tuple_val
            if len(tup) != 2:
                raise error(e_EvalError())
            if call(tup[0], [value]) is true:
                slot = as_dict(attr(case, u"slot"))
                eval_slot(ctx, slot).store(ctx, call(tup[1], [value]))
                return as_list(attr(case, u"body"))
        else:
            raise error(e_EvalError())
    if len(default) == 0:
        raise error(e_EvalError())
    return default

def eval_decl(ctx, dt, decl):
    tp = as_string(attr(decl, u"type"))
    if tp == u"method":
        op = eval_expr(ctx, as_dict(attr(decl, u"op")))
        value = eval_expr(ctx, as_dict(attr(decl, u"value")))
        op = cast(op, Operator)
        add_method(dt, op, value)
    elif tp == u"derived":
        value = eval_expr(ctx, as_dict(attr(decl, u"value")))
        for op in as_list(attr(decl, u"ops")):
            op = eval_expr(ctx, as_dict(op))
            add_method(dt, op, call(value, [dt, op]))
    elif tp == u"attr":
        name = as_string(attr(decl, u"op"))
        value = eval_expr(ctx, as_dict(attr(decl, u"value")))
        add_attr(dt, name, value, is_setter=False)
    elif tp == u"attr_set":
        name = as_string(attr(decl, u"name"))
        value = eval_expr(ctx, as_dict(attr(decl, u"value")))
        add_attr(dt, name, value, is_setter=True)
    elif tp == u"attr_method":
        name = as_string(attr(decl, u"name"))
        value = eval_expr(ctx, as_dict(attr(decl, u"value")))
        add_attr_method(dt, name, value)
    else:
        raise error(e_EvalError())

def eval_expr(ctx, val):
    tp = as_string(attr(val, u"type"))
    if tp == u"literal":
        return eval_literal(val)
    if tp == u"slot":
        return eval_slot(ctx, val).load(ctx)
    elif tp == u"assign":
        expr = eval_expr(ctx, as_dict(attr(val, u"value")))
        slot = as_dict(attr(val, u"slot"))
        eval_slot(ctx, slot).store(ctx, expr)
        return null
    elif tp == u"bind":
        module = cast(eval_expr(ctx, as_dict(attr(val, u"module"))), Module)
        for dst, src in as_dict(attr(val, u"bindings")).iteritems():
            ctx.module.bind(as_string(dst), module, as_string(src))
        return null
    elif tp == u"bind_coeffect":
        slot = eval_slot(ctx, as_dict(attr(val, u"slot")))
        fields = []
        for prop in as_list(attr(val, u"fields")):
            prop = as_dict(prop)
            name = as_string(attr(prop, u"name"))
            mutable = convert(attr(prop, u"mutable"), Bool) is true
            fields.append((name, mutable))
        coeffect = construct_coeffect(fields, ctx.module)
        slot.store(ctx, coeffect)
        return null
    elif tp == u"inplace_assign":
        op = eval_expr(ctx, as_dict(attr(val, u"op")))
        expr = eval_expr(ctx, as_dict(attr(val, u"value")))
        slot = as_dict(attr(val, u"slot"))
        slot = eval_slot(ctx, slot)
        slot.store(ctx, call(op, [slot.load(ctx), expr]))
        return null
    elif tp == u"assert":
        cond = convert(eval_expr(ctx, as_dict(attr(val, u"cond"))), Bool)
        if cond is false:
            expr = eval_expr(ctx, as_dict(attr(val, u"value")))
            loc = as_list(attr(val, u"loc"))
            tb = Traceback(e_AssertTriggered(expr))
            tb.trace.append((loc, ctx.sources))
            raise tb
        return null
    elif tp == u"raise":
        expr = eval_expr(ctx, as_dict(attr(val, u"value")))
        loc = as_list(attr(val, u"loc"))
        tb = Traceback(expr)
        tb.trace.append((loc, ctx.sources))
        raise tb
    elif tp == u"call":
        callee = as_dict(attr(val, u"callee"))
        args = as_list(attr(val, u"args"))
        v_callee = eval_expr(ctx, callee)
        v_args = []
        for arg in args:
            v_args.append(eval_expr(ctx, as_dict(arg)))
        try:
            return call(v_callee, v_args)
        except Traceback as tb:
            loc = as_list(attr(val, u"loc"))
            tb.trace.append((loc, ctx.sources))
            raise
    elif tp == u"closure":
        frame = []
        for index in as_list(attr(val, u"frame")):
            index = as_integer(index)
            frame.append(ctx.cellvars[index])
        return Closure(val, ctx.module, ctx.env, frame, ctx.sources)
    elif tp == u"cmp":
        i_exprs = as_list(attr(val, u"exprs"))
        i_ops = as_list(attr(val, u"ops"))
        if len(i_exprs) != len(i_ops) + 1:
            raise error(e_EvalError())
        l_expr = eval_expr(ctx, as_dict(i_exprs[0]))
        for i in range(0, len(i_ops)):
            op = eval_expr(ctx, as_dict(i_ops[i]))
            r_expr = eval_expr(ctx, as_dict(i_exprs[i+1]))
            if convert(call(op, [l_expr, r_expr]), Bool) is false:
                return false
            l_expr = r_expr
        return true
    elif tp == u"and":
        lhs = as_dict(attr(val, u"lhs"))
        rhs = as_dict(attr(val, u"rhs"))
        if convert(eval_expr(ctx, lhs), Bool) is true:
            return convert(eval_expr(ctx, rhs), Bool)
        else:
            return false
    elif tp == u"or":
        lhs = as_dict(attr(val, u"lhs"))
        rhs = as_dict(attr(val, u"rhs"))
        if convert(eval_expr(ctx, lhs), Bool) is true:
            return true
        else:
            return convert(eval_expr(ctx, rhs), Bool)
    elif tp == u"not":
        value = as_dict(attr(val, u"value"))
        if convert(eval_expr(ctx, value), Bool) is true:
            return false
        else:
            return true
    elif tp == u"generator":
        frame = []
        for index in as_list(attr(val, u"frame")):
            index = as_integer(index)
            frame.append(ctx.cellvars[index])
        return fresh_generator(val, ctx.module, ctx.env, frame, ctx.sources)
    elif tp == u"make_tuple":
        return Tuple([
            eval_expr(ctx, as_dict(item))
            for item in as_list(attr(val, u"items"))])
    elif tp == u"list":
        l = fresh_list()
        for value in as_list(attr(val, u"values")):
            l.list_val.append(eval_expr(ctx, as_dict(value)))
        return l
    elif tp == u"var":
        var_index = as_integer(attr(val, u"index"))
        return Freevar(var_index)
    elif tp == u"iter_once":
        value = eval_expr(ctx, as_dict(attr(val, u"value")))
        it = cast(call(op_iter, [value]), Iterator)
        slot = eval_slot(ctx, as_dict(attr(val, u"slot")))
        try:
            result, it = it.next()
        except StopIteration:
            raise error(e_NoItems())
        else:
            slot.store(ctx, it)
            return result
    elif tp == u"record":
        fields = []
        for prop in as_list(attr(val, u"fields")):
            prop = as_dict(prop)
            name = as_string(attr(prop, u"name"))
            mutable = convert(attr(prop, u"mutable"), Bool) is true
            value = eval_expr(ctx, as_dict(attr(prop, u"value")))
            fields.append((name, mutable, value))
        return construct_record(fields)
    else:
        raise error(e_EvalError())

# The slot design incorporates attributes and indices as well.
# Recognizing this duality in some expressions really
# simplified many of the utilities.
def eval_slot(ctx, slot):
    kind = as_string(attr(slot, u"kind"))
    if kind == u"local":
        index = as_integer(attr(slot, u"index"))
        return LocalSlot(index)
    elif kind == u"cell":
        index = as_integer(attr(slot, u"index"))
        return CellSlot(index)
    elif kind == u"global":
        name = as_string(attr(slot, u"name"))
        loc = as_list(attr(slot, u"loc"))
        return GlobalSlot(name, loc)
    elif kind == u"tuple":
        return TupleSlot(
            [eval_slot(ctx, as_dict(s))
                for s in as_list(attr(slot, u"slots"))],
            loc = as_list(attr(slot, u"loc")))
    elif kind == u"attr":
        base = eval_expr(ctx, as_dict(attr(slot, u"base")))
        name = as_string(attr(slot, u"name"))
        loc = as_list(attr(slot, u"loc"))
        return AttrSlot(base, name, loc)
    elif kind == u"item":
        base = eval_expr(ctx, as_dict(attr(slot, u"base")))
        index = eval_expr(ctx, as_dict(attr(slot, u"index")))
        return ItemSlot(base, index)
    elif kind == u"deref":
        value = eval_expr(ctx, as_dict(attr(slot, u"value")))
        return DerefSlot(value)
    else:
        raise error(e_EvalError())

class Slot:
    def load(self, ctx):
        raise error(e_EvalError())

    def store(self, ctx, value):
        raise error(e_EvalError())

class LocalSlot(Slot):
    def __init__(self, index):
        self.index = index

    def load(self, ctx):
        return ctx.localvars[self.index]

    def store(self, ctx, value):
        ctx.localvars[self.index] = value

class CellSlot(Slot):
    def __init__(self, index):
        self.index = index

    def load(self, ctx):
        return ctx.cellvars[self.index].val

    def store(self, ctx, value):
        ctx.cellvars[self.index].val = value

class GlobalSlot(Slot):
    def __init__(self, name, loc):
        self.name = name
        self.loc = loc
    
    def load(self, ctx):
        cell = ctx.module.face().cells.get(self.name, None)
        if cell is not None:
            return cell.load()
        for module in ctx.env:
            cell = module.face().cells.get(self.name, None)
            if cell is not None:
                return cell.load()
        else:
            tb = error(e_TypeError())
            tb.trace.append((self.loc, ctx.sources))
            raise tb

    def store(self, ctx, value):
        ctx.module.assign(self.name, value)
        # TODO: Add trace here as well.

class TupleSlot(Slot):
    def __init__(self, slots, loc):
        self.slots = slots
        self.loc = loc

    def load(self, ctx):
        return Tuple([slot.load(ctx) for slot in self.slots])

    def store(self, ctx, value):
        tup = cast(call(op_product, [value]), Tuple).tuple_val
        if len(tup) != len(self.slots):
            tb = error(e_TypeError())
            tb.trace.append((self.loc, ctx.sources))
            raise tb
        for i in range(len(tup)):
            self.slots[i].store(ctx, tup[i])

class AttrSlot(Slot):
    def __init__(self, base, name, loc):
        self.base = base
        self.name = name
        self.loc = loc

    def load(self, ctx):
        try:
            accessor = self.base.face().getattr(self.name)
            return call(accessor, [self.base])
        except Traceback as tb:
            tb.trace.append((self.loc, ctx.sources))
            raise

    def store(self, ctx, value):
        try:
            accessor = self.base.face().getattr(self.name)
            return call(accessor, [self.base, value])
        except Traceback as tb:
            tb.trace.append((self.loc, ctx.sources))
            raise

class ItemSlot(Slot):
    def __init__(self, base, index):
        self.base = base
        self.index = index

    def load(self, ctx):
        return call(op_getitem, [self.base, self.index])

    def store(self, ctx, value):
        call(op_setitem, [self.base, self.index, value])

class DerefSlot(Slot):
    def __init__(self, value):
        self.value = value

    def load(self, ctx):
        return call(op_getslot, [self.value])

    def store(self, ctx, value):
        call(op_setslot, [self.value, value])

def eval_literal(obj):
    kind = as_string(attr(obj, u"kind"))
    if kind == u"integer":
        return parse_integer(attr(obj, u"value"))
    elif kind == u"string":
        return attr(obj, u"value")
    else:
        raise error(e_EvalError())

class Cell:
    def __init__(self):
        self.val = null

def attr(val, name):
    return val[String(name)]

def as_integer(val):
    return cast(val, Integer).toint()

def as_string(val):
    return cast(val, String).string_val

def as_list(val):
    return cast(val, List).list_val

def as_dict(val):
    return cast(val, Dict).dict_val
