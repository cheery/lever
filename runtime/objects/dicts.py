from rpython.rlib.rarithmetic import intmask, r_uint
from core import *

@builtin(1)
def w_dict(iterable=None):
    result = empty_dict()
    if iterable is not None:
        Dict_update(result, iterable)
    return result

@getter(ImmutableDict, u"length", 1)
def ImmutableDict_get_length(a):
    a = cast(a, ImmutableDict)
    return wrap(len(a.table))

@getter(Dict, u"length", 1)
def Dict_get_length(a):
    a = cast(a, Dict)
    return wrap(len(a.table))

@method(ImmutableDict, op_in, 1)
def ImmutableDict_in(item, a):
    a = cast(a, ImmutableDict)
    return wrap(item in a.table)

@method(Dict, op_in, 1)
def Dict_in(item, a):
    a = cast(a, Dict)
    return wrap(item in a.table)

@conversion_to(ImmutableDict, IteratorKind)
def ImmutableDict_iter(a):
    a = cast(a, ImmutableDict).table
    return DictIterator(a.iteritems())

@conversion_to(Dict, IteratorKind)
def Dict_iter(a):
    a = cast(a, Dict).table
    return DictIterator(a.iteritems())

@method(ImmutableDict, op_eq, 1)
def ImmutableDict_eq(a, b):
    a = cast(a, ImmutableDict).table
    b = cast(b, ImmutableDict).table
    if len(a) != len(b):
        return false
    for key, item in a.iteritems():
        if key not in b:
            return false
        if not unwrap_bool(call(op_eq, [item, b[key]], 1)):
            return false
    return true

@method(ImmutableDict, op_hash, 1)
def ImmutableDict_hash(a):
    a = cast(a, ImmutableDict).table
    multi = r_uint(1822399083) + r_uint(1822399083) + 1
    hash = r_uint(1927868237)
    hash *= r_uint(len(a) + 1)
    for key, item in a.iteritems():
        h = unwrap_int(call(op_hash, [key]))
        value = (r_uint(h ^ (h << 16) ^ 89869747)  * multi)
        hash = hash ^ value
        h = unwrap_int(call(op_hash, [item]))
        value = (r_uint(h ^ (h << 16) ^ 89869747)  * multi)
        hash = hash ^ value
    hash = hash * 69069 + 907133923
    if hash == 0:
        hash = 590923713
    return wrap(intmask(hash))

@method(ImmutableDict, op_getitem, 1)
def ImmutableDict_getitem(a, item):
    a = cast(a, ImmutableDict)
    try:
        return a.table[item]
    except KeyError as _:
        raise error(e_NoIndex)

@method(Dict, op_getitem, 1)
def Dict_getitem(a, item):
    a = cast(a, Dict)
    try:
        return a.table[item]
    except KeyError as _:
        raise error(e_NoIndex)

@method(Dict, op_setitem, 0)
def Dict_setitem(a, item, value):
    a = cast(a, Dict)
    a.table[item] = value

@method(ImmutableDict, op_copy, 1)
def ImmutableDict_copy(a):
    return a

@method(Dict, op_copy, 1)
def Dict_copy(a):
    c = empty_dict()
    c.table.update(cast(a, Dict).table)
    return c

@method(Dict, op_snapshot, 1)
def Dict_snapshot(a):
    table = empty_r_dict()
    for key, item in a.table.iteritems():
        table[key] = item
    return ImmutableDict(table)

@attr_method(ImmutableDict, u"get", 1)
def get(a, item, default):
    a = cast(a, ImmutableDict)
    try:
        return a.table[item]
    except KeyError as _:
        return default

@attr_method(Dict, u"get", 1)
def get(a, item, default):
    a = cast(a, Dict)
    try:
        return a.table[item]
    except KeyError as _:
        return default

@attr_method(Dict, u"pop", 1)
def Dict_pop(a, key):
    a = cast(a, Dict)
    try:
        return a.table.pop(key)
    except KeyError as _:
        raise error(e_NoIndex)

@attr_method(ImmutableDict, u"keys", 1)
def ImmutableDict_keys(a):
    a = cast(a, ImmutableDict).table
    return KeyIterator(a.iterkeys())

@attr_method(Dict, u"keys", 1)
def Dict_keys(a):
    a = cast(a, Dict).table
    return KeyIterator(a.iterkeys())

class KeyIterator(Iterator):
    def __init__(self, iterator):
        self.iterator = iterator
        self.value = None
        self.tail = None

    def next(self):
        if self.tail is None:
            self.value = self.iterator.next()
            self.tail = KeyIterator(self.iterator)
        return self.value, self.tail

@attr_method(ImmutableDict, u"items", 1)
def ImmutableDict_items(a):
    a = cast(a, ImmutableDict).table
    return DictIterator(a.iteritems())

@attr_method(Dict, u"items", 1)
def Dict_items(a):
    a = cast(a, Dict).table
    return DictIterator(a.iteritems())

class DictIterator(Iterator):
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

@attr_method(ImmutableDict, u"values", 1)
def ImmutableDict_values(a):
    a = cast(a, ImmutableDict).table
    return ValueIterator(a.itervalues())

@attr_method(Dict, u"values", 1)
def Dict_values(a):
    a = cast(a, Dict).table
    return ValueIterator(a.itervalues())

class ValueIterator(Iterator):
    def __init__(self, iterator):
        self.iterator = iterator
        self.value = None
        self.tail = None

    def next(self):
        if self.tail is None:
            self.value = self.iterator.next()
            self.tail = ValueIterator(self.iterator)
        return self.value, self.tail

@attr_method(Dict, u"update", 0)
def Dict_update(a, items):
    a = cast(a, Dict)
    if isinstance(items, Dict):
        a.table.update(items.table)
    else:
        for item in iterate(items):
            items = cast(item, Tuple).items
            if len(items) != 2:
                raise error(e_TypeError)
            a.table[items[0]] = items[1]

variables = {
    u"dict": w_dict,
}
