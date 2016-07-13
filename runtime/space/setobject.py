from builtin import signature
from interface import Object, null
from listobject import List
from numbers import Integer
from rpython.rlib.objectmodel import compute_hash, r_dict
import space

def eq_fn(this, other):
    return this.eq(other)

def hash_fn(this):
    return this.hash()

class Set(Object):
    _immutable_fields_ = ['_set']
    __slots__ = ['_set']
    def __init__(self):
        self._set = r_dict(eq_fn, hash_fn, force_non_null=True)

    def contains(self, index):
        if index in self._set:
            return True
        return False

    def getattr(self, name):
        if name == u'length':
            return Integer(len(self._set))
        return Object.getattr(self, name)

    def iter(self):
        return SetIterator(self._set.iterkeys())

@Set.method(u"copy", signature(Set))
def Set_copy(self):
    copy = Set()
    copy._set.update(self._set)
    return copy

@Set.method(u"clear", signature(Set))
def Set_clear(self):
    self._set = r_dict(eq_fn, hash_fn, force_non_null=True)
    return null

@Set.method(u"add", signature(Set, Object))
def Set_add(self, obj):
    self._set[obj] = None
    return null

@Set.method(u"update", signature(Set, variadic=True))
def Set_update(self, argv):
    for arg in argv:
        it = arg.iter()
        try:
            while True:
                item = it.callattr(u"next", [])
                self._set[item] = None
        except StopIteration as stop:
            pass
    return null

@Set.method(u"intersection_update", signature(Set, variadic=True))
def Set_intersection_update(self, argv):
    for arg in argv:
        it = arg.iter()
        common = r_dict(eq_fn, hash_fn, force_non_null=True)
        try:
            while True:
                item = it.callattr(u"next", [])
                if item in self._set:
                    common[item] = None
        except StopIteration as stop:
            pass
        self._set = common
    return null

@Set.method(u"difference_update", signature(Set, variadic=True))
def Set_difference_update(self, argv):
    for arg in argv:
        it = arg.iter()
        try:
            while True:
                item = it.callattr(u"next", [])
                try:
                    del self._set[item]
                except KeyError as _:
                    pass
        except StopIteration as stop:
            pass
    return null

@Set.method(u"symmetric_difference_update", signature(Set, Object))
def Set_symmetric_difference_update(self, arg):
    it = as_set(arg).iter()
    try:
        while True:
            item = it.callattr(u"next", [])
            try:
                del self._set[item]
            except KeyError as _:
                self._set[item] = None
    except StopIteration as stop:
        pass
    return null

@Set.method(u"discard", signature(Set, Object))
def Set_discard(self, obj):
    try:
        del self._set[obj]
    except KeyError as _:
        pass
    return null

@Set.method(u"remove", signature(Set, Object))
def Set_remove(self, obj):
    try:
        del self._set[obj]
    except KeyError as _:
        raise space.unwind(space.LKeyError(self, obj))
    return null

@Set.method(u"pop", signature(Set))
def Set_pop(self):
    try:
        return self._set.popitem()[0]
    except KeyError as _:
        raise space.unwind(space.LKeyError(self, null))
    return null

@Set.method(u"is_disjoint", signature(Set, Object))
def Set_is_disjoint(self, arg):
    it = arg.iter()
    try:
        while True:
            item = it.callattr(u"next", [])
            if item in self._set:
                return space.false
    except StopIteration as stop:
        pass
    return space.true

@Set.method(u"is_subset", signature(Set, Object))
def Set_is_subset(self, other):
    return Set_is_superset(as_set(other), self)

@Set.method(u"is_superset", signature(Set, Object))
def Set_is_superset(self, arg):
    it = arg.iter()
    try:
        while True:
            item = it.callattr(u"next", [])
            if item not in self._set:
                return space.false
    except StopIteration as stop:
        pass
    return space.true

@Set.method(u"union", signature(Set, variadic=True))
def Set_union(self, argv):
    this = Set()
    this._set.update(self._set)
    Set_update(this, argv)
    return this

@Set.method(u"intersection", signature(Set, variadic=True))
def Set_intersection(self, argv):
    this = Set()
    this._set.update(self._set)
    Set_intersection_update(this, argv)
    return this

@Set.method(u"difference", signature(Set, variadic=True))
def Set_difference(self, argv):
    this = Set()
    this._set.update(self._set)
    Set_difference_update(this, argv)
    return this

@Set.method(u"symmetric_difference", signature(Set, Object))
def Set_symmetric_difference(self, arg):
    this = Set()
    this._set.update(self._set)
    Set_symmetric_difference_update(this, arg)
    return this

class SetIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

    def iter(self):
        return self

@SetIterator.method(u"next", signature(SetIterator))
def SetIterator_next(self):
    return self.iterator.next()

@Set.instantiator
@signature(Object, optional=1)
def instantiate(arg):
    self = Set()
    if arg is not None:
        Set_update(self, [arg])
    return self

def as_set(obj):
    if isinstance(obj, Set):
        return obj
    else:
        this = Set()
        Set_update(this, [obj])
        return this
