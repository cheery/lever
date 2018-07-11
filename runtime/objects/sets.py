from rpython.rlib.rarithmetic import intmask, r_uint
from core import *

@builtin(1)
def w_set(iterable=None):
    if iterable is None:
        return empty_set()
    else:
        result = empty_set()
        Set_update(result, iterable)
        return result

@getter(ImmutableSet, u"length", 1)
def ImmutableSet_get_length(a):
    a = cast(a, ImmutableSet).table
    return wrap(len(a))

@getter(Set, u"length", 1)
def Set_get_length(a):
    a = cast(a, Set).table
    return wrap(len(a))

@method(ImmutableSet, op_in, 1)
def ImmutableSet_in(item, a):
    a = cast(a, ImmutableSet).table
    return wrap(item in a)

@method(Set, op_in, 1)
def Set_in(item, a):
    a = cast(a, Set).table
    return wrap(item in a)

@conversion_to(ImmutableSet, IteratorKind)
def ImmutableSet_iter(a):
    a = cast(a, ImmutableSet).table
    return SetIterator(a.iterkeys())

@conversion_to(Set, IteratorKind)
def Set_iter(a):
    a = cast(a, Set).table
    return SetIterator(a.iterkeys())

class SetIterator(Iterator):
    def __init__(self, iterator):
        self.iterator = iterator
        self.value = None
        self.tail = None

    def next(self):
        if self.tail is None:
            self.value = self.iterator.next()
            self.tail = SetIterator(self.iterator)
        return self.value, self.tail

@method(ImmutableSet, op_eq, 1)
def ImmutableSet_eq(a, b):
    a = cast(a, ImmutableSet).table
    b = cast(b, ImmutableSet).table
    if len(a) != len(b):
        return false
    for item in a.iterkeys():
        if item not in b:
            return false
    return true

@method(ImmutableSet, op_hash, 1)
def ImmutableSet_hash(a):
    a = cast(a, ImmutableSet).table
    multi = r_uint(1822399083) + r_uint(1822399083) + 1
    hash = r_uint(1927868237)
    hash *= r_uint(len(a) + 1)
    for item in a.iterkeys():
        h = unwrap_int(call(op_hash, [item]))
        value = (r_uint(h ^ (h << 16) ^ 89869747)  * multi)
        hash = hash ^ value
    hash = hash * 69069 + 907133923
    if hash == 0:
        hash = 590923713
    return wrap(intmask(hash))

@method(ImmutableSet, op_copy, 1)
def ImmutableSet_copy(a):
    return a

@method(Set, op_copy, 1)
def Set_copy(a):
    c = empty_set()
    c.table.update(cast(a, Set).table)
    return c

@method(Set, op_snapshot, 1)
def Set_snapshot(a):
    table = empty_r_dict()
    table.update(cast(a, Set).table)
    return ImmutableSet(table)

@attr_method(Set, u"clear", 0)
def Set_clear(a):
    cast(a, Set).table = r_dict(eq_fn, hash_fn, force_non_null=True)

@attr_method(Set, u"add", 0)
def Set_add(a, item):
    cast(a, Set).table[item] = None

@attr_method(Set, u"update", 0)
def Set_update(a, items):
    a = cast(a, Set)
    for item in iterate(items):
        a.table[item] = None

@attr_method(Set, u"intersection_update", 0)
def Set_intersection_update(a, items):
    a = cast(a, Set)
    common = r_dict(eq_fn, hash_fn, force_non_null=True) 
    for item in iterate(items):
        if item in a.table:
            common[item] = None
    a.table = common

@attr_method(Set, u"difference_update", 0)
def Set_difference_update(a, items):
    a = cast(a, Set)
    for item in iterate(items):
        try:
            del a.table[item]
        except KeyError:
            pass

@attr_method(Set, u"symmetric_difference_update", 0)
def Set_symmetric_difference_update(a, items):
    a = cast(a, Set)
    for item in iterate(items):
        try:
            del a.table[item]
        except KeyError:
            a.table[item] = None

@attr_method(Set, u"discard", 0)
def Set_discard(a, item):
    a = cast(a, Set)
    try:
        del a.table[item]
    except KeyError:
        pass

@attr_method(Set, u"remove", 0)
def Set_remove(a, item):
    a = cast(a, Set)
    try:
        del a.table[item]
    except KeyError:
        raise error(e_NoValue)

@attr_method(Set, u"pop", 1)
def Set_pop(a):
    a = cast(a, Set)
    try:
        return a.table.popitem()[0]
    except KeyError:
        raise error(e_NoItems)

@attr_method(ImmutableSet, u"is_disjoint", 1)
def ImmutableSet_is_disjoint(a, items):
    a = cast(a, ImmutableSet)
    for item in iterate(items):
        if item in a.table:
            return false
    return true

@attr_method(Set, u"is_disjoint", 1)
def Set_is_disjoint(a, items):
    a = cast(a, Set)
    for item in iterate(items):
        if item in a.table:
            return false
    return true

@attr_method(ImmutableSet, u"is_subset", 1)
def ImmutableSet_is_subset(a, items):
    a = cast(a, ImmutableSet)
    count = 0
    for item in iterate(call(w_set, [items])):
        if item in a.table:
            count += 1
    return wrap(count == len(a.table))

@attr_method(Set, u"is_subset", 1)
def Set_is_subset(a, items):
    a = cast(a, Set)
    count = 0
    for item in iterate(call(w_set, [items])):
        if item in a.table:
            count += 1
    return wrap(count == len(a.table))

@attr_method(ImmutableSet, u"is_superset", 1)
def Set_is_superset(a, items):
    a = cast(a, ImmutableSet)
    for item in iterate(items):
        if item not in a.table:
            return false
    return true

@attr_method(Set, u"is_superset", 1)
def Set_is_superset(a, items):
    a = cast(a, Set)
    for item in iterate(items):
        if item not in a.table:
            return false
    return true

@attr_method(Set, u"union", 1)
@method(Set, op_or, 1)
def Set_union(a, items):
    a = cast(a, Set)
    result = empty_set()
    result.table.update(a.table)
    Set_update(result, items)
    return result

@attr_method(Set, u"intersection", 1)
@method(Set, op_and, 1)
def Set_intersection(a, items):
    a = cast(a, Set)
    result = empty_set()
    result.table.update(a.table)
    Set_intersection_update(result, items)
    return result

@attr_method(Set, u"difference", 1)
@method(Set, op_sub, 1)
def Set_difference(a, items):
    a = cast(a, Set)
    result = empty_set()
    result.table.update(a.table)
    Set_difference_update(result, items)
    return result

@attr_method(Set, u"symmetric_difference", 1)
@method(Set, op_xor, 1)
def Set_symmetric_difference(a, items):
    a = cast(a, Set)
    result = empty_set()
    result.table.update(a.table)
    Set_symmetric_difference_update(result, items)
    return result

# The immutable versions with set operations are quite different
# from the mutable variations, so I keep them separate.
@attr_method(ImmutableSet, u"union", 1)
@method(ImmutableSet, op_or, 1)
def ImmutableSet_union(a, items):
    table = empty_r_dict()
    table.update(cast(a, ImmutableSet).table)
    for item in iterate(items):
        table[item] = None
    return ImmutableSet(table)

@attr_method(ImmutableSet, u"intersection", 1)
@method(ImmutableSet, op_and, 1)
def ImmutableSet_intersection(a, items):
    table = empty_r_dict()
    a = cast(a, ImmutableSet)
    for item in iterate(items):
        if item in a.table:
            table[item] = None
    return ImmutableSet(table)

@attr_method(ImmutableSet, u"difference", 1)
@method(ImmutableSet, op_sub, 1)
def ImmutableSet_difference(a, items):
    table = empty_r_dict()
    table.update(cast(a, ImmutableSet).table)
    for item in iterate(items):
        try:
            table.pop(item)
        except KeyError:
            pass
    return ImmutableSet(table)

@attr_method(ImmutableSet, u"symmetric_difference", 1)
@method(ImmutableSet, op_xor, 1)
def Set_symmetric_difference(a, items):
    table = empty_r_dict()
    table.update(cast(a, ImmutableSet).table)
    for item in iterate(items):
        try:
            table.pop(item)
        except KeyError:
            table[item] = None
    return ImmutableSet(table)

variables = {
    u"set": w_set,
}
