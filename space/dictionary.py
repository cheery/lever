from rpython.rlib.objectmodel import compute_hash, r_dict
from interface import Error, Object

def eq_fn(this, other):
    return this.eq(other)

def hash_fn(this):
    return this.hash()

class Dict(Object):
    def __init__(self):
        self.data = r_dict(eq_fn, hash_fn, force_non_null=True)

    def contains(self, index):
        if index in self.data:
            return True
        return False

    def getitem(self, index):
        return self.data[index]

    def setitem(self, index, value):
        self.data[index] = value
        return value

