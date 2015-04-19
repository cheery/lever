from interface import Object
from rpython.rlib.objectmodel import compute_hash

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
