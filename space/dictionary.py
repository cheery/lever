from builtin import signature
from rpython.rlib.objectmodel import compute_hash, r_dict
from interface import Error, Object
from listobject import List
from numbers import Integer

def eq_fn(this, other):
    return this.eq(other)

def hash_fn(this):
    return this.hash()

class Dict(Object):
    _immutable_fields_ = ['data']
    def __init__(self):
        self.data = r_dict(eq_fn, hash_fn, force_non_null=True)

    def contains(self, index):
        if index in self.data:
            return True
        return False

    def getitem(self, index):
        try:
            return self.data[index]
        except KeyError as error:
            raise Error(u"key %s not in %s" % (index.repr(), self.repr()))

    def setitem(self, index, value):
        self.data[index] = value
        return value

    def iter(self):
        return KeyIterator(self.data.iterkeys())

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

@KeyIterator.builtin_method
@signature(KeyIterator)
def next(self):
    return self.iterator.next()

class ItemIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

@ItemIterator.builtin_method
@signature(ItemIterator)
def next(self):
    key, value = self.iterator.next()
    return List([key, value])

class ValueIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

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
