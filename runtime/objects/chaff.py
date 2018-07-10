from rpython.rlib.objectmodel import current_object_addr_as_int
from core import *
from modules import *
import os

def get_name(obj):
    try:
        return cast(call(op_stringify, [obj], 1), String).string
    except OperationError as op:
        if op.error.atom is not e_NoValue:
            raise
        prop = get_properties(obj)
        if prop is not None:
            docref = prop.get(atom_documentation, None)
            if docref.atom is atom_docref:
                s = docref.items[1]
                if isinstance(s, String):
                    return s.string
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
#    it = cast(args, Iterator)
#    while True:
#        try:
#            arg, it = it.next()
#        except StopIteration:
#            break
#        s = cast(call(op_stringify, [arg]), String).string_val
#        b = s.encode('utf-8')
#        os.write(1, sp + b)
#        sp = " "
#    os.write(1, "\n")

# # The stem for the base module is defined outside the entry
# # point generator. It has nearly every utility and handle that has
# # to appear in the base module.
# @builtin()
# def w_ne(a,b):
#     result = call(op_eq, [a,b])
#     result = boolean(convert(result, Bool) is false)
#     return result
# 
# @builtin()
# def w_ge(a,b):
#     i = cast(call(op_cmp, [a,b]), Integer).toint()
#     return boolean(i >= 0)
# 
# @builtin()
# def w_gt(a,b):
#     i = cast(call(op_cmp, [a,b]), Integer).toint()
#     return boolean(i == 1)
# 
# @builtin()
# def w_le(a,b):
#     i = cast(call(op_cmp, [a,b]), Integer).toint()
#     return boolean(i <= 0)
# 
# @builtin()
# def w_lt(a,b):
#     i = cast(call(op_cmp, [a,b]), Integer).toint()
#     return boolean(i == -1)
# 
# @builtin()
# def w_range(start,stop=None,step=None):
#     if stop is None:
#         stop = start
#         start = fresh_integer(0)
#     if step is None:
#         step = fresh_integer(1)
#     sign  = cast(call(op_cmp, [fresh_integer(0), step]), Integer).toint()
#     if sign == 0:
#         raise error(e_PartialOnArgument())
#     else:
#         return RangeIterator(start, stop, step, sign)
# 
# class RangeIterator(Iterator):
#     interface = Iterator.interface
#     def __init__(self, current, limit, step, sign):
#         self.current = current
#         self.limit = limit
#         self.step = step
#         self.sign = sign
# 
#     def next(self):
#         i = cast(call(op_cmp, [self.current, self.limit]), Integer).toint()
#         if i == self.sign:
#             value = self.current
#             next_value = call(op_add, [self.current, self.step])
#             k = RangeIterator(next_value, self.limit, self.step, self.sign)
#             return value, k
#         else:
#             raise StopIteration()
# 
# @builtin()
# def w_slot(value):
#     return Slot(value)
# 
# @builtin()
# def w_get_function_header(argc, opt):
#     argc = cast(argc, Integer).toint()
#     opt = cast(opt, Integer).toint()
#     return func_interfaces.get(argc, opt)
# 
# @python_bridge
# def w_construct_set(items=None):
#     if items is None:
#         return fresh_set()
#     return construct_set(items)
# 
# @python_bridge
# def w_construct_dict(pairs=None):
#     if pairs is None:
#         return fresh_dict()
#     return construct_dict(pairs)
# 
# @python_bridge
# def w_construct_list(items=None):
#     if items is None:
#         return fresh_list()
#     return construct_list(items)
# 
# @python_bridge
# def w_single(items):
#     it = cast(call(op_iter, [items]), Iterator)
#     try:
#         x, it = it.next()
#     except StopIteration:
#         raise error(e_PartialOnArgument())
#     try:
#         y, it = it.next()
#     except StopIteration:
#         return x
#     else:
#         raise error(e_PartialOnArgument())
# 
# @python_bridge
# def w_unique_coercion(items):
#     faces = {}
#     it = cast(call(op_iter, [items]), Iterator)
#     while True:
#         try:
#             x, it = it.next()
#             if not isinstance(x, Interface):
#                 raise error(e_TypeError())
#             faces[x] = None
#         except StopIteration:
#             break
#     face = unique_coercion(faces)
#     if face is None:
#         raise error(e_NoValue())
#     return face
# 
# @python_bridge
# def w_is_closure(item):
#     if isinstance(item.face(), FunctionInterface):
#         return true
#     else:
#         return false
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
# 
# @python_bridge
# def w_once(iterator):
#     if not isinstance(iterator, Iterator):
#         iterator = cast(call(op_iter, [iterator]), Iterator)
#     try:
#         x, it = iterator.next()
#     except StopIteration:
#         raise error(e_NoValue())
#     return Tuple([x, it])

# base_stem = {
#     u"==": op_eq,
#     u"!=": w_ne,
#     u"hash": op_hash,
#     u"in": op_in,
#     u"getitem": op_getitem,
#     u"setitem": op_setitem,
#     u"iter": op_iter,
#     u"cmp": op_cmp,
#     u">=": w_ge,
#     u">": w_gt,
#     u"<=": w_le,
#     u"<": w_lt,
#     u"++": op_concat,
#     u"copy": op_copy,
#     u"-expr": op_neg,
#     u"+expr": op_pos,
#     u"+": op_add,
#     u"-": op_sub,
#     u"*": op_mul,
#     u"%": op_mod,
#     u"~expr": op_not,
#     u"&": op_and,
#     u"|": op_or,
#     u"xor": op_xor,
#     u"stringify": op_stringify,
#     u"parse_integer": builtin()(parse_integer),
#     u"true" : true,
#     u"false": false,
#     u"range": w_range,
#     u"slot": w_slot,
#     u"set": w_construct_set,
#     u"dict": w_construct_dict,
#     u"list": w_construct_list,
#     u"call_with_coeffects": w_call_with_coeffects,
#     u"face": builtin()(lambda x: x.face()),
#     u"Parameter": TypeParameter.interface,
# #    u"by_reference": w_by_reference,
# #    u"by_value": w_by_value,
# #    u"parameter": builtin()(lambda x: TypeParameter(cast(x, Integer))),
# #    u"get_function_header": w_get_function_header,
# #    u"single": w_single,
#     u"inspect": interpreter.w_inspect,
# #    u"unique_coercion": w_unique_coercion,
# #    u"is_closure": w_is_closure,
# #    u"get_dom": builtin()(lambda i: common.dom.get(cast(i, Integer).toint())),
# #    u"cod": common.cod,
# #    u"is_subtype": w_is_subtype,
#     u"placeholder_error": w_placeholder_error,
#     u"once": w_once,
# }

variables = {
    u"input": w_input,
    u"print": w_print,
}
