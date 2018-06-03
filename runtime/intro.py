from json_loader import read_json_file
from objects import *
from context import (
    CoeffectModuleCell,
    init_executioncontext,
    construct_coeffect,
    w_call_with_coeffects )
import interpreter
import os

def new_entry_point(config, interpret=False):
    base_module = Module()
    for name in base_stem:
        base_module.assign(name, base_stem[name])

    BasicIO = construct_coeffect([
        (u"input", False), (u"print", False)], base_module)
    base_module.assign(u"BasicIO", BasicIO)

    def entry_point_a(raw_argv):
        init_executioncontext({
            BasicIO: construct_record([
                (u"input", False, w_input),
                (u"print", False, w_print) ])
        })
        try:
            mspace = ModuleSpace(
                local = String(u'prelude'),
                env = [base_module],
                loader = w_json_loader)
            call(w_import, [mspace, String(u"intro")])
        except Traceback as tb:
            os.write(0, "Traceback (most recent call last):\n")
            for loc, sources in reversed(tb.trace):
                col0 = cast(loc[0], Integer).toint()
                lno0 = cast(loc[1], Integer).toint()
                col1 = cast(loc[2], Integer).toint()
                lno1 = cast(loc[3], Integer).toint()
                srci = cast(loc[4], Integer).toint()
                src = sources[srci].string_val.encode('utf-8')
                s = "  %d %d %d %d %s\n" % (col0, lno0, col1, lno1, src)
                os.write(0, s)
            os.write(0, tb.error.__class__.__name__ + "\n")
        return 0

    # This smaller version can be used during interpretation
    # if you want more traceback than what the earlier entry
    # point can do.
    def entry_point_b(raw_argv):
        init_executioncontext({
            BasicIO: construct_record([
                (u"input", False, w_input),
                (u"print", False, w_print) ])
        })
        mspace = ModuleSpace(
            local = String(u'prelude'),
            env = [base_module],
            loader = w_json_loader)
        call(w_import, [mspace, String(u"intro")])

    if not interpret:
        return entry_point_a
    else:
        return entry_point_b

@builtin()
def w_json_loader(mspace, name):
    mspace = cast(mspace, ModuleSpace)
    name = cast(name, String).string_val
    local = cast(mspace.local, String).string_val
    src = local + u"/" + name + u".lc.json"
    obj = read_json_file(String(src))
    env = mspace.env
    script, module = interpreter.read_script(obj,
        {u'import': prefill(w_import, [mspace])}, env)
    call(script, [])
    return module

# The BasicIO is our first coeffect. It provides some basic
# input/output that helps when writing the early programs. 
@builtin()
def w_input(prompt):
    os.write(0, cast(prompt, String).string_val.encode('utf-8'))
    line = os.read(0, 1024)
    return String(line.decode('utf-8'))

@builtin(vari=True)
def w_print(args):
    sp = ""
    for arg in args:
        s = cast(call(op_stringify, [arg]), String).string_val
        b = s.encode('utf-8')
        os.write(1, sp + b)
        sp = " "
    os.write(1, "\n")

# The stem for the base module is defined outside the entry
# point generator. It has nearly every utility and handle that has
# to appear in the base module.
@builtin()
def w_ne(a,b):
    result = call(op_eq, [a,b])
    result = boolean(convert(result, Bool) is false)
    return result

@builtin()
def w_ge(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i >= 0)

@builtin()
def w_gt(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i == 1)

@builtin()
def w_le(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i <= 0)

@builtin()
def w_lt(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i == -1)

@builtin()
def w_range(start,stop=None,step=None):
    if stop is None:
        stop = start
        start = fresh_integer(0)
    if step is None:
        step = fresh_integer(1)
    sign  = cast(call(op_cmp, [fresh_integer(0), step]), Integer).toint()
    if sign == 0:
        raise error(e_PartialOnArgument())
    else:
        return RangeIterator(start, stop, step, sign)

class RangeIterator(Iterator):
    interface = Iterator.interface
    def __init__(self, current, limit, step, sign):
        self.current = current
        self.limit = limit
        self.step = step
        self.sign = sign

    def next(self):
        i = cast(call(op_cmp, [self.current, self.limit]), Integer).toint()
        if i == self.sign:
            value = self.current
            next_value = call(op_add, [self.current, self.step])
            k = RangeIterator(next_value, self.limit, self.step, self.sign)
            return value, k
        else:
            raise StopIteration()

@builtin()
def w_slot(value):
    return Slot(value)

@builtin()
def w_get_function_header(argc, vari, opt):
    argc = cast(argc, Integer).toint()
    vari = convert(vari, Bool) is true
    opt = cast(opt, Integer).toint()
    return func_interfaces.get(argc, vari, opt)

@python_bridge
def w_construct_set(items=None):
    if items is None:
        return fresh_set()
    return construct_set(items)

@python_bridge
def w_construct_dict(pairs=None):
    if pairs is None:
        return fresh_dict()
    return construct_dict(pairs)

@python_bridge
def w_construct_list(items=None):
    if items is None:
        return fresh_list()
    return construct_list(items)

@python_bridge
def w_single(items):
    it = cast(call(op_iter, [items]), Iterator)
    try:
        x, it = it.next()
    except StopIteration:
        raise error(e_PartialOnArgument())
    try:
        y, it = it.next()
    except StopIteration:
        return x
    else:
        raise error(e_PartialOnArgument())

base_stem = {
    u"==": op_eq,
    u"!=": w_ne,
    u"hash": op_hash,
    u"call": op_call,
    u"in": op_in,
    u"getitem": op_getitem,
    u"setitem": op_setitem,
    u"iter": op_iter,
    u"cmp": op_cmp,
    u">=": w_ge,
    u">": w_gt,
    u"<=": w_le,
    u"<": w_lt,
    u"++": op_concat,
    u"copy": op_copy,
    u"-expr": op_neg,
    u"+expr": op_pos,
    u"+": op_add,
    u"-": op_sub,
    u"*": op_mul,
    u"~expr": op_not,
    u"&": op_and,
    u"|": op_or,
    u"xor": op_xor,
    u"stringify": op_stringify,
    u"parse_integer": builtin()(parse_integer),
    u"null": null,
    u"true" : true,
    u"false": false,
    u"range": w_range,
    u"slot": w_slot,
    u"set": w_construct_set,
    u"dict": w_construct_dict,
    u"list": w_construct_list,
    u"call_with_coeffects": w_call_with_coeffects,
    u"NoItems": e_NoItems.interface,
    u"NoIndex": e_NoIndex.interface,
    u"face": builtin()(lambda x: x.face()),
    u"Bool": Bool,
    u"Integer": Integer.interface,
    u"Set": Set.interface,
    u"List": List.interface,
    u"Dict": Dict.interface,
    u"String": String.interface,
    u"Parameter": TypeParameter.interface,
    u"by_reference": w_by_reference,
    u"by_value": w_by_value,
    u"parameter": builtin()(lambda x: TypeParameter(cast(x, Integer))),
    u"get_function_header": w_get_function_header,
    u"single": w_single,
    u"inspect": interpreter.w_inspect,
}
