from interface import Object
from rpython.rlib.objectmodel import compute_hash

class String(Object):
    def __init__(self, string):
        self.string = string

    # Not fixing the string here, fix later
    def repr(self):
        return '"' + str(self.string) + '"'

    def hash(self):
        return compute_hash(self.string)

    def eq(self, other):
        return self.string == other.string
