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

        self.cellvars = as_list(attr(code, u"cellvars"))
        self.localvars = as_list(attr(code, u"localvars"))

        if as_string(attr(code, u"type")) == u"script":
            self.args = []
            self.body = as_list(attr(code, u"body"))
            self.loc  = [fresh_integer(0)] * 5
        elif as_string(attr(code, u"type")) == u"function":
            self.args = as_list(attr(code, u"args"))
            self.body = as_list(attr(code, u"body"))
            self.loc  = as_list(attr(code, u"loc"))
        else:
            raise error(e_EvalError())

        self.function_face = closure_interfaces.get(
            len(self.args), False, 0)

    def face(self):
        return self.function_face

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
    return eval_program(ctx, stack)

w_call_closure = python_bridge(call_closure, vari=True)

class EvaluationContext:
    def __init__(self, localvars, cellvars, module, env, sources):
        self.localvars = localvars
        self.cellvars = cellvars
        self.module = module
        self.env = env
        self.sources = sources

# TODO: add a flag telling whether it's function or
# generator we are running. allow/disallow return/yield.


# The evaluator is layered and now really distinguishes
# between statements and functions. That makes it easier to
# implement but also, I never really used the 'if' as
# an expression in the previous interpreters for
# readability reasons.
def eval_program(ctx, stack):
    try:
        while len(stack) > 0:
            body, start, mod = stack.pop()
            for i in range(start, len(body)):
                stmt = as_dict(body[i])
                tp = as_string(attr(stmt, u"type"))
                if tp == u"return":
                    expr = as_dict(attr(stmt, u"value"))
                    return eval_expr(ctx, expr)
                #elif tp == u"yield":
                #    expr = as_dict(attr(stmt, u"value"))
                #    stack.append((body, i+1, mod))
                #    return eval_expr(ctx, expr)
                #elif tp == u"repeat":
                #    fresh = as_list(attr(stmt, u"fresh"))
                #    branch = as_list(attr(stmt, u"body"))
                #    stack.append((body, i+1, mod))
                #    stack.append((branch, 0, Loop(fresh)))
                #    break
                #elif tp == u"cond":
                #    cond = as_dict(attr(stmt, u"cond"))
                #    cond = eval_expr(ctx, cond)
                #    if cast(cond, Bool) is true:
                #        branch = as_list(attr(stmt, u"t_body"))
                #        stack.append((body, i+1, mod))
                #        stack.append((branch, 0, None))
                #        break
                #    else:
                #        branch = as_list(attr(stmt, u"f_body"))
                #        stack.append((body, i+1, mod))
                #        stack.append((branch, 0, None))
                #        break
                #else:
                eval_expr(ctx, stmt)
            if isinstance(mod, Loop):
                for index in mod.fresh:
                    index = as_integer(index)
                    ctx.cellvars[index] = Cell()
                stack.append((body, 0, mod))
    finally:
        while len(stack) > 0:
            stack.pop()
    return null

#@setter(Generator, "next",
#    signature(Generator, returns=Object))
#def Generator_next(generator):
#    try:
#        return eval_generator(generator)
#    except StopIteration as _:
#        raise error(e_StopIteration())

#def eval_generator(generator):
#    stack = generator.stack
#    ctx = EvaluationContext(
#        generator.module, generator.env,
#        generator.cellvars, generator.localvars)
#    result = eval_program(ctx, stack)
#    if len(stack) == 0:
#        raise StopIteration()
#    else:
#        return result

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
    elif tp == u"function":
        frame = []
        for index in as_list(attr(val, u"frame")):
            index = as_integer(index)
            frame.append(ctx.cellvars[index])
        return Closure(val, ctx.module, ctx.env, frame, ctx.sources)
#    elif tp == u"generator":
#        frame = []
#        for index in as_list(attr(val, u"frame")):
#            index = as_integer(index)
#            frame.append(ctx.cellvars[index])
#        return Generator(val, ctx.module, ctx.env, frame)
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

class Loop:
    def __init__(self, fresh):
        self.fresh = fresh


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
