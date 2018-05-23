from common import *

@getter(List.interface, u"length")
def List_get_length(a):
    return fresh_integer(len(a.list_val))

@method(List.interface, op_getitem)
def List_getitem(a, index):
    index = cast(index, Integer).toint()
    if index < len(a.list_val):
        return a.list_val[index]
    raise error(e_PartialOnArgument())

@method(List.interface, op_setitem)
def List_setitem(a, index, value):
    index = cast(index, Integer).toint()
    if index < len(a.list_val):
        a.list_val[index] = value
        return null
    raise error(e_PartialOnArgument())
