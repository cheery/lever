from builtin import signature
from interface import Object, null
from rpython.rlib.listsort import make_timsort_class
from rpython.rlib.rarithmetic import intmask
from numbers import Integer
import space

class List(Object):
    _immutable_fields_ = ['contents']
    __slots__ = ['contents']
    def __init__(self, contents):
        self.contents = contents

    def __getitem__(self, index):
        return self.contents[index]

    def __len__(self):
        return len(self.contents)

    def hash(self):
        mult = 1000003
        x = 0x345678
        z = len(self.contents)
        for item in self.contents:
            y = item.hash()
            x = (x ^ y) * mult
            z -= 1
            mult += 82520 + z + z
        x += 97531
        return intmask(x)

    def eq(self, other):
        if not isinstance(other, List):
            return False
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if not self[i].eq(other[i]):
                return False
        return True

    def getattr(self, name):
        if name == u'length':
            return Integer(len(self.contents))
        return Object.getattr(self, name)

    def contains(self, item):
        for obj in self.contents:
            if obj.eq(item):
                return True
        return False
    
    def getitem(self, index):
        if not isinstance(index, Integer):
            raise space.unwind(space.LTypeError(u"index not an integer"))
        if not 0 <= index.value < len(self.contents):
            raise space.unwind(space.LKeyError(self, index))
        return self.contents[index.value]

    def setitem(self, index, value):
        if not isinstance(index, Integer):
            raise space.unwind(space.LTypeError(u"index not an integer"))
        if not 0 <= index.value < len(self.contents):
            raise space.unwind(space.LKeyError(self, index))
        self.contents[index.value] = value
        return value

    def iter(self):
        return ListIterator(iter(self.contents))

    def repr(self):
        out = []
        for item in self.contents:
            out.append(item.repr())
        return u'[' + u', '.join(out) + u']'

@List.method(u"append", signature(List, Object))
def List_append(self, other):
    self.contents.append(other)
    return null

@List.method(u"extend", signature(List, Object))
def List_extend(self, iterable):
    it = iterable.iter()
    try:
        while True:
            self.contents.append(it.callattr(u"next", []))
    except StopIteration as stop:
        return space.null
    return space.null

@List.method(u"insert", signature(List, Integer, Object))
def List_insert(self, index, obj):
    val = index.value
    if not 0 <= val <= len(self.contents):
        raise space.unwind(space.LKeyError(self, index))
    self.contents.insert(val, obj)
    return space.null

@List.method(u"remove", signature(List, Object))
def List_remove(self, obj):
    for index, item in enumerate(self.contents):
        if item.eq(obj):
            self.contents.pop(index)
            return space.null
    raise space.unwind(space.LValueError(self, obj))

@List.method(u"pop", signature(List, Integer, optional=1))
def List_pop(self, index):
    if index:
        index = index.value
    else:
        index = len(self.contents) - 1
    if not 0 <= index < len(self.contents):
        raise space.unwind(space.LKeyError(self, space.Integer(index)))
    return self.contents.pop(index)

@List.method(u"index", signature(List, Object))
def List_index(self, obj):
    for index, item in enumerate(self.contents):
        if item.eq(obj):
            return Integer(index)
    raise space.unwind(space.LValueError(self, obj))

@List.method(u"count", signature(List, Object))
def List_count(self, obj):
    count = 0
    for item in self.contents:
        if item.eq(obj):
            count += 1
    return Integer(count)

@List.method(u"sort", signature(List, Object, optional=1))
def List_sort(self, lt):
    if not lt:
        lt = space.operators.lt
    sorter = ListSort(self.contents, len(self.contents))
    sorter.w_lt = lt
    self.contents = []
    sorter.sort()
    self.contents = sorter.list
    return space.null
#    def sorter_sorting(a, b):
#        x = sorter.call([a, b])
#        if isinstance(x, space.Integer):
#            return x.value
#        else:
#            raise space.unwind(space.LTypeError(u"expected .sort cmp to return integers"))
##    else:
##        def ordinary_sorting(a, b):
##
#    self.contents.sort(sorter_sorting)
#    return space.null

@List.method(u"reverse", signature(List))
def List_reverse(self):
    self.contents.reverse()
    return space.null

class ListIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

    def iter(self):
        return self

@ListIterator.builtin_method
@signature(ListIterator)
def next(self):
    return self.iterator.next()

@List.instantiator
def instantiate(argv):
    list_ = List([])
    if len(argv) > 0:
        other = argv[0]
        it = other.iter()
        try:
            while True:
                list_.contents.append(it.callattr(u"next", []))
        except StopIteration as stop:
            pass
    return list_

TimSort = make_timsort_class()

class ListSort(TimSort):
    def lt(self, a, b):
        return space.is_true(self.w_lt.call([a, b]))
