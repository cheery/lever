from interface import Object
from rpython.rlib.objectmodel import compute_hash

class String(Object):
    def __init__(self, string):
        #assert isinstance(string, unicode)
        self.string = string

    # Not fixing the string here, fix later
    def repr(self):
        return u'"' + self.string + u'"'

    def hash(self):
        return compute_hash(self.string)

    def eq(self, other):
        return self.string == other.string
