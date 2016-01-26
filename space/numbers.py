from interface import Object, Error, null
from rpython.rlib.objectmodel import compute_hash
from builtin import signature

class Float(Object):
    _immutable_fields_ = ['number']
    __slots__ = ['number']
    __attrs__ = ['number']
    def __init__(self, number):
        self.number = number

    def repr(self):
        return u"%f" % self.number

    def hash(self):
        return compute_hash(self.number)

    def eq(self, other):
        if isinstance(other, Float):
            return self.number == other.number
        return False

class Integer(Object):
    _immutable_fields_ = ['value']
    __slots__ = ['value']
    __attrs__ = ['value']
    def __init__(self, value):
        self.value = value

    def repr(self):
        return u"%d" % self.value

    def hash(self):
        return compute_hash(self.value)

    def eq(self, other):
        if isinstance(other, Integer):
            return self.value == other.value
        return False

class Boolean(Object):
    _immutable_fields_ = ['flag']
    __slots__ = ['flag']
    __attrs__ = ['flag']
    def __init__(self, flag):
        self.flag = flag

    def repr(self):
        if self.flag:
            return u"true"
        else:
            return u"false"

Boolean.interface.parent = Integer.interface

def to_float(obj):
    if isinstance(obj, Float):
        return obj.number
    elif isinstance(obj, Integer):
        return float(obj.value)
    elif isinstance(obj, Boolean):
        if is_true(obj):
            return 1.0
        else:
            return 0.0
    else:
        raise Error(u"expected float value")

def to_int(obj):
    if isinstance(obj, Float):
        return int(obj.number)
    elif isinstance(obj, Integer):
        return obj.value
    elif isinstance(obj, Boolean):
        if is_true(obj):
            return 1
        else:
            return 0
    else:
        raise Error(u"expected int value")

true = Boolean(True)
false = Boolean(False)

def is_true(flag):
    return flag is not null and flag is not false

def is_false(flag):
    return flag is null or flag is false

def boolean(cond):
    return true if cond else false

@Float.instantiator
@signature(Object)
def instantiate(obj):
    return Float(to_float(obj))

@Integer.instantiator
@signature(Object)
def instantiate(obj):
    return Integer(to_int(obj))

@Boolean.instantiator
@signature(Object)
def instantiate(obj):
    return boolean(is_true(obj))
