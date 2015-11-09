from interface import Object
from rpython.rlib.objectmodel import compute_hash
import numbers

class Uint8Array(Object):
    _immutable_fields_ = ['uint8data']
    __slots__ = ['uint8data']
    def __init__(self, uint8data):
        self.uint8data = uint8data

    def repr(self): # Add hexadecimal formatting later..
        return u"<uint8array>"

    def hash(self):
        return compute_hash(self.uint8data)

    def eq(self, other):
        if isinstance(other, Uint8Array):
            return self.uint8data == other.uint8data
        return False

    def getattr(self, name):
        if name == u'length':
            return numbers.Integer(len(self.uint8data))
        return Object.getattr(self, name)
