from builtin import signature
from interface import Object
from rpython.rlib.objectmodel import compute_hash
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rgc
from rpython.rlib.runicode import str_decode_utf_8
import numbers
import space

class Uint8Data(Object):
    _immutable_fields_ = ['uint8data', 'length']
    __slots__ = ['uint8data', 'length']
    def __init__(self, uint8data, length):
        self.uint8data = uint8data
        self.length = length

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
        if isinstance(index, space.Slice):
            start, stop, step = index.clamped(0, self.length)
            if step != 1:
                result = [] # TODO: keep it as Uint8Array?
                for i in range(start, stop, step):
                    result.append(numbers.Integer(rffi.r_long(self.uint8data[i])))
                return space.List(result)
            return Uint8Slice(rffi.ptradd(self.uint8data, start), stop - start, self)
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

    def to_str(self):
        return rffi.charpsize2str(
            rffi.cast(rffi.CCHARP, self.uint8data),
            int(self.length))

@Uint8Data.method(u'memcpy', signature(Uint8Data, Uint8Data, numbers.Integer, optional=1))
def Uint8Data_memcpy(self, src, size):
    size = src.length if size is None else size.value
    if size > self.length or size > src.length:
        raise space.unwind(space.LError(u"memcpy range error"))
    rffi.c_memcpy(
        rffi.cast(rffi.VOIDP, self.uint8data),
        rffi.cast(rffi.VOIDP, src.uint8data), size)
    return space.null

class Uint8Array(Uint8Data):
    _immutable_fields_ = ['uint8data', 'length']
    __slots__ = ['uint8data', 'length']
    def repr(self): # Add hexadecimal formatting later..
        return u"<uint8array>"

    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self.uint8data, flavor='raw')

class Uint8Slice(Uint8Data):
    _immutable_fields_ = ['uint8data', 'length', 'parent']
    __slots__ = ['uint8data', 'length', 'parent']
    def __init__(self, base, length, parent):
        Uint8Data.__init__(self, base, length)
        self.parent = parent

    def repr(self): # Add hexadecimal formatting later..
        return u"<uint8slice>"

    def getattr(self, name):
        if name == u'parent':
            return self.parent
        return Uint8Data.getattr(self, name)

def alloc_uint8array(length):
    return Uint8Array(
        lltype.malloc(rffi.UCHARP.TO, length, flavor='raw'),
        length)

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

class Utf8Decoder(Object):
    __slots__ = ['buffer']
    def __init__(self):
        self.buffer = ''

    def call(self, argv):
        return utf8_decoder_call([self] + argv)

@Utf8Decoder.instantiator2(signature())
def Utf8Decoder_init():
    return Utf8Decoder()

@signature(Utf8Decoder, Uint8Data)
def utf8_decoder_call(self, data):
    return space.String(utf8_decoder_operate(self, data.to_str(), False))

@Utf8Decoder.method(u"finish", signature(Utf8Decoder))
def Utf8Decoder_finish(self):
    return space.String(utf8_decoder_operate(self, '', True))

def utf8_decoder_operate(decoder, newdata, final):
    data = decoder.buffer + newdata
    try:
        string, pos = str_decode_utf_8(
            data, len(data), '', final=final)
    except UnicodeDecodeError as error:
        raise space.unwind(space.LError(u"unicode decode failed"))
    decoder.buffer = data[pos:]
    return string


class Uint8Builder(Object):
    __slots__ = ['buffers', 'array', 'total_capacity', 'avail', 'current']
    def __init__(self):
        self.buffers = []
        self.total_capacity = 0
        self.array = None
        self.avail = 0
        self.current = lltype.nullptr(rffi.VOIDP.TO)

    def __del__(self):
        for buf, sz in self.buffers:
            lltype.free(buf, flavor='raw')
        self.buffers = []

@Uint8Builder.instantiator2(signature())
def Uint8Builder_init():
    return Uint8Builder()

@Uint8Builder.method(u"append", signature(Uint8Builder, Uint8Data))
def Uint8Builder_append(self, obj):
    data = rffi.cast(rffi.VOIDP, obj.uint8data)
    remaining = obj.length
    if remaining > 0 and self.avail > 0:
        count = min(remaining, self.avail)
        rffi.c_memcpy(self.current, data, count)
        remaining -= count
        data = rffi.ptradd(data, count)
        self.avail -= count
        self.current = rffi.ptradd(self.current, count)
    if remaining > 0: # self.avail == 0
        capacity = (remaining + 1023) & ~1023
        base = lltype.malloc(rffi.VOIDP.TO, self.avail, flavor='raw')
        self.avail = capacity
        self.current = rffi.cast(rffi.VOIDP, base)
        self.buffers.append((base, capacity))
        self.total_capacity += capacity
    # remaining > avail
    rffi.c_memcpy(self.current, data, remaining)
    self.avail -= remaining
    self.current = rffi.ptradd(self.current, remaining)
    return space.null
    
@Uint8Builder.method(u"build", signature(Uint8Builder))
def Uint8Builder_build(self):
    if self.array and self.array.length == self.total_capacity:
        return self.array
    # Folding buffers together is only necessary if more
    # stuff was appanded in the behind.
    length = self.total_capacity - self.avail
    base = lltype.malloc(rffi.VOIDP.TO, length, flavor='raw')
    remaining = length
    current = base
    if self.array is not None:
        rffi.c_memcpy(current,
            rffi.cast(rffi.VOIDP, self.array.uint8data),
            self.array.length)
        current = rffi.ptradd(current, self.array.length)
        remaining -= self.array.length
    for buf, sz in self.buffers:
        sz = min(sz, remaining)
        rffi.c_memcpy(current, buf, sz)
        current = rffi.ptradd(current, sz)
        remaining -= sz
        lltype.free(buf, flavor='raw')
    self.buffers = []

    base = rffi.cast(rffi.UCHARP, base)
    self.array = Uint8Array(base, length)
    self.total_capacity = length
    self.avail = 0
    return self.array
