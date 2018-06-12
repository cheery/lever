from rpython.rlib.objectmodel import r_dict
from booleans import boolean
from common import *

def construct_dict(iterable):
    d = fresh_dict()
    Dict_update(d, iterable)
    return d

def fresh_dict():
    return Dict(r_dict(eq_fn, hash_fn, force_non_null=True))

@getter(Dict.interface, u"length")
def Dict_get_length(a):
    return fresh_integer(len(a.dict_val))

@method(Dict.interface, op_in)
def Dict_in(item, a):
    a = cast(a, Dict)
    return boolean(item in a.dict_val)

@method(Dict.interface, op_iter)
def Dict_iter(a):
    a = cast(a, Dict).dict_val
    return DictIterator(a.iteritems())

@method(Dict.interface, op_getitem)
def Dict_getitem(a, item):
    a = cast(a, Dict)
    try:
        return a.dict_val[item]
    except KeyError:
        raise error(e_NoIndex())

@method(Dict.interface, op_setitem)
def Dict_setitem(a, item, value):
    a = cast(a, Dict)
    a.dict_val[item] = value

@method(Dict.interface, op_copy)
def Dict_copy(a):
    c = fresh_dict()
    c.dict_val.update(cast(a, Dict).dict_val)
    return c

@attr_method(Dict.interface, u"get")
def get(a, item, default):
    a = cast(a, Dict)
    try:
        return a.dict_val[item]
    except KeyError:
        return default

@attr_method(Dict.interface, u"pop")
def Dict_pop(a, key):
    a = cast(a, Dict)
    try:
        return a.dict_val.pop(key)
    except KeyError:
        raise error(e_NoIndex())

@attr_method(Dict.interface, u"keys")
def Dict_keys(a):
    a = cast(a, Dict).dict_val
    return KeyIterator(a.iterkeys())

class KeyIterator(Iterator):
    interface = Iterator.interface

    def __init__(self, iterator):
        self.iterator = iterator
        self.value = None
        self.tail = None

    def next(self):
        if self.tail is None:
            self.value = self.iterator.next()
            self.tail = KeyIterator(self.iterator)
        return self.value, self.tail

@attr_method(Dict.interface, u"items")
def Dict_items(a):
    a = cast(a, Dict).dict_val
    return DictIterator(a.iteritems())

class DictIterator(Iterator):
    interface = Iterator.interface

    def __init__(self, iterator):
        self.iterator = iterator
        self.value = None
        self.tail = None

    def next(self):
        if self.tail is None:
            k,v = self.iterator.next()
            self.value = Tuple([k,v])
            self.tail = DictIterator(self.iterator)
        return self.value, self.tail

@attr_method(Dict.interface, u"values")
def Dict_values(a):
    a = cast(a, Dict).dict_val
    return ValueIterator(a.itervalues())

class ValueIterator(Iterator):
    interface = Iterator.interface

    def __init__(self, iterator):
        self.iterator = iterator
        self.value = None
        self.tail = None

    def next(self):
        if self.tail is None:
            self.value = self.iterator.next()
            self.tail = ValueIterator(self.iterator)
        return self.value, self.tail

@attr_method(Dict.interface, u"update")
def Dict_update(a, items):
    a = cast(a, Dict)
    if isinstance(items, Dict):
        a.dict_val.update(items.dict_val)
    else:
        it = call(op_iter, [items])
        while True:
            try:
                x, it = it.next()
            except StopIteration:
                break
            else:
                tup = cast(x, Tuple).tuple_val
                if len(tup) != 2:
                    raise error(e_TypeError())
                a.dict_val[tup[0]] = tup[1]
