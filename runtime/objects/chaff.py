from rpython.rlib.objectmodel import current_object_addr_as_int
from core import *
from modules import *
import os

def get_name(obj, show_arity=True):
    if isinstance(obj, Compound):
        prefix = get_name(obj.atom, show_arity=False)
        items = []
        for item in obj.items:
            items.append(get_name(item))
        return prefix + u"(" + u", ".join(items) + u")"
    if isinstance(obj, ImmutableList) or isinstance(obj, List):
        items = [get_name(item) for item in iterate(obj)]
        return u"[" + u", ".join(items) + u"]"
    if isinstance(obj, Tuple):
        items = [get_name(item) for item in obj.items]
        return u"(" + u", ".join(items) + u")"
    try:
        return cast(call(op_stringify, [obj], 1), String).string
    except OperationError as op:
        if op.error.atom is not e_NoValue:
            raise
        prop = get_properties(obj)
        if prop is not None:
            docref = prop.get(atom_documentation, None)
            if docref and docref.atom is atom_docref:
                s = docref.items[1]
                if isinstance(s, String):
                    if isinstance(obj, Atom) and show_arity and obj.arity > 0:
                        return s.string + ("/%s" % obj.arity).decode('utf-8')
                    return s.string
        if isinstance(obj, Builtin):
            return (u"<Builtin %s>" % obj.function_name)
        if isinstance(obj, BuiltinPortal):
            return (u"<BuiltinPortal %s>" % obj.function_name)
        obj_id = current_object_addr_as_int(obj)
        return ("<%s %s>" % (obj.__class__.__name__, obj_id)).decode('utf-8')

@builtin(1)
def w_input(prompt):
    os.write(0, cast(prompt, String).string.encode('utf-8'))
    line = os.read(0, 1024)
    return String(line.decode('utf-8'))
 
@builtin(0)
def w_print(arg):
    s = get_name(arg)
    b = s.encode('utf-8')
    os.write(1, b + "\n")

#@builtin(0)
#def w_print_many(args):
#    sp = ""
#    for arg in iterate(args):
#        s = cast(call(op_stringify, [arg]), String).string
#        b = s.encode('utf-8')
#        os.write(1, sp + b)
#        sp = " "
#    os.write(1, "\n")

@builtin(1)
def w_ne(a,b):
    return wrap(not unwrap_bool(call(op_eq, [a,b], 1)))

@builtin(1)
def w_ge(a,b):
    i = unwrap_int(call(op_cmp, [a,b]))
    return wrap(i >= 0)

@builtin(1)
def w_gt(a,b):
    i = unwrap_int(call(op_cmp, [a,b]))
    return wrap(i == 1)

@builtin(1)
def w_le(a,b):
    i = unwrap_int(call(op_cmp, [a,b]))
    return wrap(i <= 0)

@builtin(1)
def w_lt(a,b):
    i = unwrap_int(call(op_cmp, [a,b]))
    return wrap(i == -1)

@builtin(1)
def w_range(start,stop=None,step=None):
    if stop is None:
        stop = start
        start = wrap(0)
    if step is None:
        step = wrap(1)
    sign  = unwrap_int(call(op_cmp, [wrap(0), step]))
    if sign == 0:
        raise error(e_PreconditionFailed)
    else:
        return RangeIterator(start, stop, step, sign)

class RangeIterator(Iterator):
    def __init__(self, current, limit, step, sign):
        self.current = current
        self.limit = limit
        self.step = step
        self.sign = sign

    def next(self):
        i = unwrap_int(call(op_cmp, [self.current, self.limit]))
        if i == self.sign:
            value = self.current
            next_value = call(op_add, [self.current, self.step])
            k = RangeIterator(next_value, self.limit, self.step, self.sign)
            return value, k
        else:
            raise StopIteration()

# @builtin()
# def w_get_function_header(argc, opt):
#     argc = cast(argc, Integer).toint()
#     opt = cast(opt, Integer).toint()
#     return func_interfaces.get(argc, opt)
# 
# @python_bridge
# def w_is_subtype(a, b):
#     if a is b:
#         return true
#     elif isinstance(a, FunctionInterface) and isinstance(b, FunctionInterface):
#         if a.argc - a.opt <= b.argc <= a.argc:
#             return true
#         return false
#     else:
#         return false
 
@builtin(1)
def w_single(items):
    it = cast(items, Iterator)
    try:
        x, it = it.next()
    except StopIteration:
        raise error(e_PreconditionFailed)
    try:
        y, it = it.next()
    except StopIteration:
        return x
    else:
        raise error(e_PreconditionFailed)

@builtin(2)
def w_once(iterator):
    iterator = cast(iterator, Iterator)
    try:
        x, it = iterator.next()
    except StopIteration:
        raise error(e_NoValue)
    return Tuple([x, it])

@builtin(1)
def w_kind(obj):
    return obj.kind

#     u"parse_integer": builtin()(parse_integer),
#     u"call_with_coeffects": w_call_with_coeffects,
#     u"Parameter": TypeParameter.interface,
# #    u"by_reference": w_by_reference,
# #    u"by_value": w_by_value,
# #    u"parameter": builtin()(lambda x: TypeParameter(cast(x, Integer))),
# #    u"get_function_header": w_get_function_header,
#     u"inspect": interpreter.w_inspect,
# #    u"unique_coercion": w_unique_coercion,
# #    u"is_closure": w_is_closure,
# #    u"get_dom": builtin()(lambda i: common.dom.get(cast(i, Integer).toint())),
# #    u"cod": common.cod,
# #    u"is_subtype": w_is_subtype,
#     u"placeholder_error": w_placeholder_error,

@builtin(1)
def w_Atom(w_arity, w_properties=None):
    atom = Atom(unwrap_int(w_arity))
    if w_properties is None:
        return atom
    for item in iterate(w_properties):
        items = cast(item, Tuple).items
        if len(items) != 2:
            raise error(e_TypeError)
        operator.properties[items[0]] = items[1]
    return atom

@builtin(1)
def w_Operator(w_selectors, w_argc, w_properties, default=None):
    selectors = []
    for sel in iterate(w_selectors):
        selectors.append(unwrap_int(sel))
    argc = unwrap_int(w_argc)
    operator = Operator(selectors, argc, default)
    for item in iterate(w_properties):
        items = cast(item, Tuple).items
        if len(items) != 2:
            raise error(e_TypeError)
        operator.properties[items[0]] = items[1]
    return operator

@builtin(1)
def w_has_properties(obj):
    return wrap(isinstance(obj, KObject))

@builtin(1)
def w_enumerate(obj, index=wrap(0)):
    return Enumerator(cast(obj, Iterator), unwrap_int(index))

class Enumerator(Iterator):
    def __init__(self, iterator, index):
        self.iterator = iterator
        self.index = index

    def next(self):
        x, iterator = self.iterator.next()
        return Tuple([wrap(self.index), x]), Enumerator(iterator, self.index+1)


variables = {
    u"repr": builtin(1)(lambda a: wrap(get_name(a))),
    u"input": w_input,
    u"print": w_print,
    u"!=": w_ne,
    u">=": w_ge,
    u">": w_gt,
    u"<=": w_le,
    u"<": w_lt,
    u"range": w_range,
    u"single": w_single,
    u"once": w_once,
    u"kind": w_kind,
    u"Atom": w_Atom,
    u"Operator": w_Operator,
    u"has_properties": w_has_properties,
    u"get_attribute": builtin(1)(get_attribute),
    u"set_attribute": builtin(0)(set_attribute),
    u"enumerate": w_enumerate,
}
