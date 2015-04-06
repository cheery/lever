from interface import Object
from rpython.rlib.objectmodel import compute_hash

class Integer(Object):
    def __init__(self, value):
        self.value = value

    def repr(self):
        return str(self.value)

    def hash(self):
        return compute_hash(self.value)

    def eq(self, other):
        return self.value == other.value

class Boolean(Object):
    def __init__(self, flag):
        self.flag = flag

    def repr(self):
        if self.flag:
            return "true"
        else:
            return "false"

Boolean.interface.parent = Integer.interface
