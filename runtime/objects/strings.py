from common import *

@method(String.interface, op_eq)
def String_eq(a, b):
    a = cast(a, String)
    b = cast(b, String)
    if a.string_val == b.string_val:
        return true
    else:
        return false

@method(String.interface, op_hash)
def String_hash(a):
    a = cast(a, String)
    return fresh_integer(compute_hash(a.string_val))

@method(String.interface, op_getitem)
def String_getitem(a, index):
    a = cast(a, String)
    index = cast(a, Integer).toint()
    return String(a.string_val[index])

#@method(String.interface, op_iter)
#def String_iter(a):

@method(String.interface, op_cmp)
def String_cmp(a, b):
    if a.string_val < b.string_val:
        return fresh_integer(-1)
    elif a.string_val > b.string_val:
        return fresh_integer(+1)
    else:
        return fresh_integer(0)

@method(String.interface, op_concat)
def String_concat(a, b):
    a = cast(a, String)
    b = cast(b, String)
    return String(a.string_val + b.string_val)
