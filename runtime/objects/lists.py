from core import *
from rpython.rlib.listsort import make_timsort_class
from rpython.rlib.rarithmetic import intmask, r_uint

@builtin(1)
def w_list(iterable=None):
    if iterable is None:
        return List([])
    else:
        result = List([])
        List_extend(result, iterable)
        return result

@getter(ImmutableList, u"length", 1)
def ImmutableList_get_length(a):
    a = cast(a, ImmutableList).contents
    return wrap(len(a))

@getter(List, u"length", 1)
def List_get_length(a):
    a = cast(a, List).contents
    return wrap(len(a))

@method(ImmutableList, op_eq, 1)
def ImmutableList_eq(a, b):
    a = cast(a, ImmutableList).contents
    b = cast(b, ImmutableList).contents
    if len(a) != len(b):
        return false
    for i in range(len(a)):
        if not unwrap_bool(call(op_eq, [a[i], b[i]])):
            return false
    return true

@method(ImmutableList, op_hash, 1)
def ImmutableList_hash(a, w_hash):
    a = cast(a, ImmutableList).contents
    mult = 1000003
    x = 0x345678
    z = len(a)
    for w_item in a:
        y = unwrap_int(call(w_hash, [w_item]))
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return wrap(intmask(x))

@method(List, op_snapshot, 1)
def List_snapshot(a):
    contents = []
    for item in cast(a, List).contents:
        contents.append(item)
    return ImmutableList(contents)

@method(ImmutableList, op_concat, 1)
def ImmutableList_concat(a, b):
    a = cast(a, ImmutableList)
    b = cast(b, ImmutableList)
    return ImmutableList(a.contents + b.contents)

@method(List, op_concat, 1)
def List_concat(a, b):
    a = cast(a, List).contents
    b = cast(b, List).contents
    return List(a + b)

@method(ImmutableList, op_copy, 1)
def ImmutableList_copy(a):
    return a

@method(List, op_copy, 1)
def List_copy(a):
    return List(list(cast(a, List).contents))

@method(ImmutableList, op_in, 1)
def ImmutableList_in(item, a):
    a = cast(a, ImmutableList).contents
    return wrap(item in a)

@method(List, op_in, 1)
def List_in(item, a):
    a = cast(a, List).contents
    return wrap(item in a)

@method(ImmutableList, op_getitem, 1)
def ImmutableList_getitem(a, index):
    a = cast(a, ImmutableList)
    index = unwrap_int(index)
    if index < len(a.contents):
        return a.contents[index]
    raise error(e_NoIndex)

@method(List, op_getitem, 1)
def List_getitem(a, index):
    a = cast(a, List)
    index = unwrap_int(index)
    if index < len(a.contents):
        return a.contents[index]
    raise error(e_NoIndex)

@method(List, op_setitem, 0)
def List_setitem(a, index, value):
    a = cast(a, List)
    index = unwrap_int(index)
    if index < len(a.contents):
        a.contents[index] = value
    else:
        raise error(e_NoIndex)

@conversion_to(ImmutableList, IteratorKind)
def ImmutableList_iter(a):
    return ListIterator(0, a.contents)

@conversion_to(List, IteratorKind)
def List_iter(a):
    return ListIterator(0, a.contents)

class ListIterator(Iterator):
    def __init__(self, index, contents):
        self.index = index
        self.contents = contents

    def next(self):
        if self.index < len(self.contents):
            k = ListIterator(self.index+1, self.contents)
            return self.contents[self.index], k
        raise StopIteration()

@attr_method(List, u"append", 0)
def List_append(a, item):
    a = cast(a, List)
    a.contents.append(item)

@attr_method(List, u"extend", 0)
def List_extend(a, items):
    a = cast(a, List)
    for item in iterate(items):
        a.contents.append(item)

@attr_method(List, u"insert", 0)
def List_insert(a, index, obj):
    a = cast(a, List)
    index = unwrap_int(index)
    if not 0 <= index <= len(a.contents):
        raise error(e_PreconditionFailed)
    a.contents[index] = obj

@attr_method(List, u"remove", 0)
def List_remove(a, obj):
    a = cast(a, List)
    for index, item in enumerate(a.contents):
        if unwrap_bool(call(op_eq, [item, obj])):
            a.contents.pop(index)
            break
    else:
        raise error(e_NoValue)

@attr_method(List, u"pop", 1)
def List_pop(a, index=None):
    a = cast(a, List)
    if index is None:
        index = len(a.contents) - 1
    else:
        index = unwrap_int(index)
    if not 0 <= index <= len(a.contents):
        raise error(e_NoIndex)
    return a.contents.pop(index)

@attr_method(ImmutableList, u"index", 1)
def ImmutableList_index(a, obj):
    a = cast(a, ImmutableList)
    for index, item in enumerate(a.contents):
        if unwrap_bool(call(op_eq, [item, obj])):
            return wrap(index)
    raise error(e_NoValue)

@attr_method(List, u"index", 1)
def List_index(a, obj):
    a = cast(a, List)
    for index, item in enumerate(a.contents):
        if unwrap_bool(call(op_eq, [item, obj])):
            return wrap(index)
    raise error(e_NoValue)

@attr_method(ImmutableList, u"count", 1)
def ImmutableList_count(a, obj):
    a = cast(a, ImmutableList)
    count = 0
    for item in a.contents:
        if unwrap_bool(call(op_eq, [item, obj])):
            count += 1
    return wrap(count)

@attr_method(List, u"count", 1)
def List_count(a, obj):
    a = cast(a, List)
    count = 0
    for item in a.contents:
        if unwrap_bool(call(op_eq, [item, obj])):
            count += 1
    return wrap(count)

@attr_method(List, u"reverse", 0)
def List_reverse(a):
    a = cast(a, List)
    a.contents.reverse()

@attr_method(List, u"sort", 0)
def List_sort(a, w_cmp = op_cmp):
    a = cast(a, List)
    sorter = ListSort(a.contents, len(a.contents))
    sorter.w_cmp = w_cmp
    a.contents = []
    sorter.sort()
    a.contents = sorter.list

TimSort = make_timsort_class()

class ListSort(TimSort):
    def lt(self, a, b):
        n = unwrap_int(call(self.w_cmp, [a,b]))
        return n < 0

variables = {
    u"list": w_list,
}
