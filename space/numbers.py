from interface import Object
from rpython.rlib.objectmodel import compute_hash

class Float(Object):
    _immutable_fields_ = ['number']
    def __init__(self, number):
        self.number = number

    def repr(self):
        return u"%f" % self.number

    def hash(self):
        return compute_hash(self.number)

    def eq(self, other):
        return self.number == other.number

class Integer(Object):
    _immutable_fields_ = ['value']
    def __init__(self, value):
        self.value = value

    def repr(self):
        return u"%d" % self.value

    def hash(self):
        return compute_hash(self.value)

    def eq(self, other):
        return self.value == other.value

class Boolean(Object):
    _immutable_fields_ = ['flag']
    def __init__(self, flag):
        self.flag = flag

    def repr(self):
        if self.flag:
            return u"true"
        else:
            return u"false"

Boolean.interface.parent = Integer.interface
