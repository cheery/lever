from rpython.rlib.objectmodel import r_dict
from rpython.rlib.rarithmetic import intmask, r_uint
from booleans import boolean
from common import *

def construct_set(iterable):
    s = fresh_set()
    Set_update(s, iterable)
    return s

def fresh_set():
    return Set(r_dict(eq_fn, hash_fn, force_non_null=True))

@getter(Set.interface, u"length")
def Set_get_length(a):
    a = cast(a, Set).set_val
    return fresh_integer(len(a))

@method(Set.interface, op_in)
def Set_in(item, a):
    a = cast(a, Set).set_val
    return boolean(item in a)

@method(Set.interface, op_iter)
def Set_iter(a):
    a = cast(a, Set).set_val
    return SetIterator(a.iterkeys())

class SetIterator(Iterator):
    interface = Iterator.interface

    def __init__(self, iterator):
        self.iterator = iterator
        self.value = None
        self.tail = None

    def next(self):
        if self.tail is None:
            self.value = self.iterator.next()
            self.tail = SetIterator(self.iterator)
        return self.value, self.tail

@method(Set.interface, op_eq)
def Set_eq(a, b):
    a = cast(a, Set).set_val
    b = cast(b, Set).set_val
    if len(a) != len(b):
        return false
    for item in a.iterkeys():
        if item not in b:
            return false
    return true

@method(Set.interface, op_hash)
def Set_hash(a):
    a = cast(a, Set).set_val
    multi = r_uint(1822399083) + r_uint(1822399083) + 1
    hash = r_uint(1927868237)
    hash *= r_uint(len(a) + 1)
    for w_item in a.iterkeys():
        h = cast(call(op_hash, [w_item]), Integer).toint()
        value = (r_uint(h ^ (h << 16) ^ 89869747)  * multi)
        hash = hash ^ value
    hash = hash * 69069 + 907133923
    if hash == 0:
        hash = 590923713
    return fresh_integer(intmask(hash))

@method(Set.interface, op_copy)
def Set_copy(a):
    c = fresh_set()
    c.set_val.update(cast(a, Set).set_val)
    return c

@attr_method(Set.interface, u"clear")
def Set_clear(a):
    cast(a, Set).set_val = r_dict(eq_fn, hash_fn, force_non_null=True)

@attr_method(Set.interface, u"add")
def Set_add(a, item):
    cast(a, Set).set_val[item] = None

@attr_method(Set.interface, u"update")
def Set_update(a, items):
    a = cast(a, Set)
    it = call(op_iter, [items])
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        else:
            a.set_val[x] = None

@attr_method(Set.interface, u"intersection_update")
def Set_intersection_update(a, items):
    a = cast(a, Set)
    it = call(op_iter, [items])
    common = r_dict(eq_fn, hash_fn, force_non_null=True) 
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        else:
            if x in a.set_val:
                common[x] = None
    a.set_val = common

@attr_method(Set.interface, u"difference_update")
def Set_difference_update(a, items):
    a = cast(a, Set)
    it = call(op_iter, [items])
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        else:
            try:
                del a.set_val[x]
            except KeyError:
                pass

@attr_method(Set.interface, u"symmetric_difference_update")
def Set_symmetric_difference_update(a, items):
    a = cast(a, Set)
    it = call(op_iter, [items])
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        else:
            try:
                del a.set_val[x]
            except KeyError:
                a.set_val[x] = None

@attr_method(Set.interface, u"discard")
def Set_discard(a, item):
    a = cast(a, Set)
    try:
        del a.set_val[item]
    except KeyError:
        pass

@attr_method(Set.interface, u"remove")
def Set_remove(a, item):
    a = cast(a, Set)
    try:
        del a.set_val[item]
    except KeyError:
        raise error(e_NoValue())

@attr_method(Set.interface, u"pop")
def Set_pop(a):
    a = cast(a, Set)
    try:
        return a.set_val.popitem()[0]
    except KeyError:
        raise error(e_NoItems())

@attr_method(Set.interface, u"is_disjoint")
def Set_is_disjoint(a, items):
    a = cast(a, Set)
    it = call(op_iter, [items])
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        else:
            if x in a.set_val:
                return false
    return true

@attr_method(Set.interface, u"is_subset")
def Set_is_subset(a, items):
    a = cast(a, Set)
    it = call(op_iter, [items])
    count = 0
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        else:
            if x in a.set_val:
                count += 1
    return boolean(count == len(a.set_val))

@attr_method(Set.interface, u"is_superset")
def Set_is_superset(a, items):
    a = cast(a, Set)
    it = call(op_iter, [items])
    while True:
        try:
            x, it = it.next()
        except StopIteration:
            break
        else:
            if x not in a.set_val:
                return false
    return true

@attr_method(Set.interface, u"union")
@method(Set.interface, op_or)
def Set_union(a, items):
    a = cast(a, Set)
    result = fresh_set()
    result.set_val.update(a.set_val)
    Set_update(result, items)
    return result

@attr_method(Set.interface, u"intersection")
@method(Set.interface, op_and)
def Set_intersection(a, items):
    a = cast(a, Set)
    result = fresh_set()
    result.set_val.update(a.set_val)
    Set_intersection_update(result, items)
    return result

@attr_method(Set.interface, u"difference")
@method(Set.interface, op_sub)
def Set_difference(a, items):
    a = cast(a, Set)
    result = fresh_set()
    result.set_val.update(a.set_val)
    Set_difference_update(result, items)
    return result

@attr_method(Set.interface, u"symmetric_difference")
@method(Set.interface, op_xor)
def Set_symmetric_difference(a, items):
    a = cast(a, Set)
    result = fresh_set()
    result.set_val.update(a.set_val)
    Set_symmetric_difference_update(result, items)
    return result
