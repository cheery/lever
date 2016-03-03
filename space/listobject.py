from builtin import signature
from interface import Object, null
from rpython.rlib.rarithmetic import intmask
from numbers import Integer
from errors import OldError

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
            raise OldError(u"index not an integer")
        if not 0 <= index.value < len(self.contents):
            raise OldError(u"index out of range")
        return self.contents[index.value]

    def setitem(self, index, value):
        if not isinstance(index, Integer):
            raise OldError(u"index not an integer")
        if not 0 <= index.value < len(self.contents):
            raise OldError(u"index out of range")
        self.contents[index.value] = value
        return value

    def iter(self):
        return ListIterator(iter(self.contents))

    def repr(self):
        out = []
        for item in self.contents:
            out.append(item.repr())
        return u'[' + u', '.join(out) + u']'

@List.builtin_method
@signature(List, Object)
def append(self, other):
    self.contents.append(other)
    return null

class ListIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

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
