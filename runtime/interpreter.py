from objects import *

def read_script(code, preset, env):
    module = Module()
    for key, value in preset.items():
        module.assign(key, value)
    code = as_dict(code)
    sources = as_list(attr(code, u"sources"))
    return Closure(code, module, env, [], sources)

# Closures have similar challenges as what builtin functions
# have.
class ClosureInterface(FunctionInterface):
    def method(self, op):
        if op is op_call:
            return w_call_closure
        return FunctionInterface.method(self, op)

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
        eval_slot_set(ctx, slot, args[i])
    stack = [(closure.body, 0, None)]
    try:
        res = eval_program(ctx, stack)
    finally:
        while len(stack) > 0:
            stack.pop()
    return res

w_call_closure = python_bridge(call_closure, vari=True)

# Generators are incredibly much more simpler than Closures
# because we do not give them an argument list.
class Generator(Iterator):
    interface = Iterator.interface
    def __init__(self, code, module, env, frame, sources):
        self.module = module
        self.env = env
        self.sources = sources

        cellvars = as_list(attr(code, u"cellvars"))
        localvars = as_list(attr(code, u"localvars"))
        body = as_list(attr(code, u"body"))
        self.cellvars = frame + [
            Cell()
            for _ in range(len(frame), len(cellvars))]
        self.localvars = [null
            for _ in range(len(localvars))]
        self.stack = [(body, 0, None)]

    def next(self):
        if len(self.stack) == 0:
            raise StopIteration()
        ctx = EvaluationContext(
            self.localvars, self.cellvars,
            self.module, self.env, self.sources,
            is_generator=True)
        try:
            result = eval_program(ctx, self.stack)
        except:
            while len(self.stack) > 0:
                self.stack.pop()
            raise
        if len(self.stack) == 0:
            raise StopIteration()
        else:
            return result

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
        for i in range(start, len(body)):
            stmt = as_dict(body[i])
            tp = as_string(attr(stmt, u"type"))
            if tp == u"return" and not ctx.is_generator:
                expr = as_dict(attr(stmt, u"value"))
                return eval_expr(ctx, expr)
            elif tp == u"yield" and ctx.is_generator:
                expr = as_dict(attr(stmt, u"value"))
                stack.append((body, i+1, mod))
                return eval_expr(ctx, expr)
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
                    mod  = None
                    break
                else:
                    stack.append((body, i+1, mod))
                    body = as_list(attr(stmt, u"fbody"))
                    stack.append((body, 0, None))
                    mod  = None
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
    return null

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

class Loop:
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
        self.iterator = cast(eval_expr(ctx, self.value), Iterator)
        return self.step(ctx)

    def step(self, ctx):
        try:
            eval_slot_set(ctx, self.slot, self.iterator.next())
            return True
        except StopIteration:
            return False

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

def eval_expr(ctx, val):
    tp = as_string(attr(val, u"type"))
    if tp == u"literal":
        return eval_literal(val)
    if tp == u"slot":
        return eval_slot_get(ctx, val)
    elif tp == u"assign":
        expr = eval_expr(ctx, as_dict(attr(val, u"value")))
        slot = as_dict(attr(val, u"slot"))
        eval_slot_set(ctx, slot, expr)
        return null
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
            raise tb
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
        return Generator(val, ctx.module, ctx.env, frame, ctx.sources)
    else:
        raise error(e_EvalError())

# The slot design eventually incorporates attributes and
# indices as well. Recognizing this duality in some
# expressions has really simplified many of the utilities.
def eval_slot_get(ctx, slot):
    kind = as_string(attr(slot, u"kind"))
    if kind == u"local":
        index = as_integer(attr(slot, u"index"))
        return ctx.localvars[index]
    elif kind == u"cell":
        index = as_integer(attr(slot, u"index"))
        return ctx.cellvars[index].val
    elif kind == u"global":
        name = as_string(attr(slot, u"name"))
        cell = ctx.module.face().cells.get(name, None)
        if cell is not None:
            return cell.val
        for module in ctx.env:
            cell = module.face().cells.get(name, None)
            if cell is not None:
                return cell.val
        else:
            loc = as_list(attr(slot, u"loc"))
            tb = error(e_TypeError())
            tb.trace.append((loc, ctx.sources))
            raise tb
#    elif kind == u"attr":
#        name = as_string(attr(val, u"name"))
#        base = eval_expr(ctx, as_dict(attr(val, u"base")))
#        return getattr(base, name)
#    elif kind == u"index":
#        base = eval_expr(ctx, as_dict(attr(val, u"base")))
#        index = eval_expr(ctx, as_dict(attr(val, u"index")))
#        return getitem(base, index)
    else:
        raise error(e_EvalError())

def eval_slot_set(ctx, slot, val):
    kind = as_string(attr(slot, u"kind"))
    if kind == u"local":
        index = as_integer(attr(slot, u"index"))
        ctx.localvars[index] = val
    elif kind == u"cell":
        index = as_integer(attr(slot, u"index"))
        ctx.cellvars[index].val = val
    elif kind == u"global":
        name = as_string(attr(slot, u"name"))
        ctx.module.assign(name, val)
        # TODO: Add trace here as well.
#    elif kind == u"attr":
#        name = as_string(attr(val, u"name"))
#        base = eval_expr(ctx, as_dict(attr(val, u"base")))
#        index = eval_expr(ctx, as_dict(attr(val, u"index")))
#        return setattr(base, name, val)
#    elif kind == u"index":
#        base = eval_expr(ctx, as_dict(attr(val, u"base")))
#        index = eval_expr(ctx, as_dict(attr(val, u"index")))
#        return setitem(base, index, val)
    else:
        raise error(e_EvalError())

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
