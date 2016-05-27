from builtin import signature
from rpython.rlib.objectmodel import compute_hash, r_dict
from interface import Object
from listobject import List
from numbers import Integer
import space

def eq_fn(this, other):
    return this.eq(other)

def hash_fn(this):
    return this.hash()

class Dict(Object):
    _immutable_fields_ = ['data']
    __slots__ = ['data']
    def __init__(self):
        self.data = r_dict(eq_fn, hash_fn, force_non_null=True)

    def contains(self, index):
        if index in self.data:
            return True
        return False

    def getattr(self, name):
        if name == u'length':
            return Integer(len(self.data))
        return Object.getattr(self, name)

    def getitem(self, index):
        try:
            return self.data[index]
        except KeyError as _:
            raise space.unwind(space.LKeyError(self, index))

    def setitem(self, index, value):
        self.data[index] = value
        return value

    def iter(self):
        return KeyIterator(self.data.iterkeys())

@Dict.builtin_method
def get(argv):
    if len(argv) == 2:
        v0 = argv[0]
        v1 = argv[1]
        v2 = space.null
    else:
        assert len(argv) == 3
        v0 = argv[0]
        v1 = argv[1]
        v2 = argv[2]
    assert isinstance(v0, Dict)
    try:
        return v0.data[v1]
    except KeyError as error:
        return v2

@Dict.builtin_method
@signature(Dict)
def keys(self):
    return KeyIterator(self.data.iterkeys())

@Dict.builtin_method
@signature(Dict)
def items(self):
    return ItemIterator(self.data.iteritems())

@Dict.builtin_method
@signature(Dict)
def values(self):
    return ValueIterator(self.data.itervalues())

class KeyIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

    def iter(self):
        return self

@KeyIterator.builtin_method
@signature(KeyIterator)
def next(self):
    return self.iterator.next()

class ItemIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

    def iter(self):
        return self

@ItemIterator.builtin_method
@signature(ItemIterator)
def next(self):
    key, value = self.iterator.next()
    return List([key, value])

class ValueIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

    def iter(self):
        return self

@ValueIterator.builtin_method
@signature(ValueIterator)
def next(self):
    return self.iterator.next()

@Dict.instantiator
def instantiate(argv):
    dict_ = Dict()
    if len(argv) > 0:
        other = argv[0]
        if isinstance(other, Dict):
            dict_.data.update(other.data)
        else:
            it = other.iter()
            try:
                while True:
                    item = it.callattr(u"next", [])
                    key = item.getitem(Integer(0))
                    val = item.getitem(Integer(1))
                    dict_.setitem(key, val)
            except StopIteration as stop:
                pass
    return dict_
