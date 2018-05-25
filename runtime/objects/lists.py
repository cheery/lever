from rpython.rlib.listsort import make_timsort_class
from common import *

def fresh_list():
    return List([])

@getter(List.interface, u"length")
def List_get_length(a):
    return fresh_integer(len(a.list_val))

@method(List.interface, op_eq)
def List_eq(a, b):
    a = cast(a, List).list_val
    b = cast(b, List).list_val
    if len(a) != len(b):
        return false
    for i in range(len(a)):
        if convert(call(op_eq, [a[i], b[i]]), Bool) is false:
            return false
    return true

@method(List.interface, op_concat)
def List_concat(a, b):
    a = cast(a, List).list_val
    b = cast(b, List).list_val
    return List(a + b)

@method(List.interface, op_copy)
def List_copy(a):
    return List(list(cast(a, Dict).dict_val))

@method(List.interface, op_in)
def List_in(item, a):
    a = cast(a, List).list_val
    if item in a:
        return true
    else:
        return false

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

@method(List.interface, op_iter)
def List_iter(a):
    return ListIterator(0, a.list_val)

class ListIterator(Iterator):
    interface = Iterator.interface
    def __init__(self, index, list_val):
        self.index = index
        self.list_val = list_val

    def next(self):
        if self.index < len(self.list_val):
            k = ListIterator(self.index+1, self.list_val)
            return self.list_val[self.index], k
        raise StopIteration()

@attr_method(List.interface, u"append")
def List_append(a, item):
    a = cast(a, List)
    a.list_val.append(item)

@attr_method(List.interface, u"extend")
def List_extend(a, items):
    a = cast(a, List)
    it = cast(call(op_iter, [items]), Iterator)
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        a.list_val.append(x)

@attr_method(List.interface, u"insert")
def List_insert(a, index, obj):
    a = cast(a, List)
    index = cast(index, Integer).toint()
    if not 0 <= index <= len(a.list_val):
        raise error(e_PartialOnArgument())
    a.list_val[index] = obj

@attr_method(List.interface, u"remove")
def List_remove(a, obj):
    a = cast(a, List)
    for index, item in enumerate(a.list_val):
        if convert(call(op_eq, [item, obj]), Bool) is true:
            a.list_val.pop(index)
            break
    else:
        raise error(e_PartialOnArgument())

@attr_method(List.interface, u"pop")
def List_pop(a, index=null):
    a = cast(a, List)
    if index is null:
        index = len(a.list_val) - 1
    else:
        index = cast(index, Integer).toint()
    if not 0 <= index <= len(a.list_val):
        raise error(e_PartialOnArgument())
    return a.list_val.pop(index)

@attr_method(List.interface, u"index")
def List_index(a, obj):
    a = cast(a, List)
    for index, item in enumerate(a.list_val):
        if convert(call(op_eq, [item, obj]), Bool) is true:
            return fresh_integer(index)
    raise error(e_PartialOnArgument())

@attr_method(List.interface, u"count")
def List_count(a, obj):
    count = 0
    for item in a.list_val:
        if convert(call(op_eq, [item, obj]), Bool) is true:
            count += 1
    return fresh_integer(count)

@attr_method(List.interface, u"reverse")
def List_reverse(a):
    a.list_val.reverse()

@attr_method(List.interface, u"sort")
def List_sort(a, w_cmp = op_cmp):
    a = cast(a, List)
    sorter = ListSort(a.list_val, len(a.list_val))
    sorter.w_cmp = w_cmp
    a.list_val = []
    sorter.sort()
    a.list_val = sorter.list

TimSort = make_timsort_class()

class ListSort(TimSort):
    def lt(self, a, b):
        n = cast(call(self.w_cmp, [a,b]), Integer).toint()
        return n < 0

