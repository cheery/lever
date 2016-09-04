from builtin import signature
from interface import Object
from rpython.rlib.objectmodel import compute_hash
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rgc
import numbers
import space

class Uint8Array(Object):
    _immutable_fields_ = ['uint8data', 'length']
    __slots__ = ['uint8data', 'length']
    def __init__(self, uint8data, length):
        self.uint8data = uint8data
        self.length = length

    def repr(self): # Add hexadecimal formatting later..
        return u"<uint8array>"

    #def hash(self):
    #    return compute_hash(self.uint8data)

    #def eq(self, other):
    #    if isinstance(other, Uint8Array):
    #        return self.uint8data == other.uint8data
    #    return False

    def getattr(self, name):
        if name == u'length':
            return numbers.Integer(self.length)
        return Object.getattr(self, name)
        
    def getitem(self, index):
        index = space.cast(index, numbers.Integer, u"index not an integer")
        if not 0 <= index.value < self.length:
            raise space.unwind(space.LKeyError(self, index))
        return numbers.Integer(rffi.r_long(self.uint8data[index.value]))

    def setitem(self, index, value):
        index = space.cast(index, numbers.Integer, u"index not an integer")
        if not 0 <= index.value < self.length:
            raise space.unwind(space.LKeyError(self, index))
        value = space.cast(value, numbers.Integer, u"value not an integer")
        self.uint8data[index.value] = rffi.r_uchar(value.value)
        return value

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self.uint8data, flavor='raw')

def to_uint8array(cstring):
    return Uint8Array(rffi.cast(rffi.UCHARP, rffi.str2charp(cstring)), len(cstring))

@Uint8Array.instantiator
@signature(Object)
def _(obj):
    if isinstance(obj, space.Integer):
        return Uint8Array(lltype.malloc(rffi.UCHARP.TO, obj.value, flavor='raw'), obj.value)
    if isinstance(obj, space.List):
        length = len(obj.contents)
        array = Uint8Array(lltype.malloc(rffi.UCHARP.TO, length, flavor='raw'), length)
        for i in range(0, length):
            x = obj.contents[i]
            if isinstance(x, space.Integer):
                array.uint8data[i] = rffi.r_uchar(x.value)
            else:
                raise space.OldError(u"Value of incorrect type: " + x.repr())
        return array
    it = obj.iter()
    out = []
    try:
        while True:
            x = it.callattr(u"next", [])
            if isinstance(x, space.Integer):
                out.append(rffi.r_uchar(x.value))
            else:
                raise space.OldError(u"Value of incorrect type: " + x.repr())
    except StopIteration as stop:
        pass
    length = len(out)
    uint8data = lltype.malloc(rffi.UCHARP.TO, length, flavor='raw')
    for i in range(0, length):
        uint8data[i] = out[i]
    return Uint8Array(uint8data, length)
