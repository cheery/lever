from rpython.rlib import jit_libffi, clibffi, unroll
from rpython.rtyper.lltypesystem import rffi, lltype
from space import Error, Object, Integer
# Simple, platform independent concepts are put up
# here, so they won't take space elsewhere.

class Type(Object):
    parameter = None # Some of the C types are parametric
                     # it's ok.
    size = 0  # These fields remain zero if it's an
    align = 0 # opaque type.

# Many systems are sensitive to memory alignment
def align(x, a):
    return x + (a - x % a) % a

def sizeof(tp):
    assert isinstance(tp, Type)
    if tp.size == 0 or tp.align == 0:
        raise Error("cannot determine size of opaque type")
    return tp.size

# This is something rpython's allocator is doing, and
# it looks nice enough. Allocations are treated as arrays,
# in parametric records the parameter is treated as an array.
def sizeof_a(tp, n):
    assert isinstance(tp, Type)
    if tp.size == 0 or tp.align == 0:
        raise Error("cannot determine size of opaque type")
    if tp.parameter is not None:
        return tp.size + sizeof(tp.parameter)*n
    else:
        return tp.size * n

signed_types = unroll.unrolling_iterable([rffi.LONG, rffi.INT, rffi.SHORT, rffi.CHAR])
unsigned_types = unroll.unrolling_iterable([rffi.ULONG, rffi.UINT, rffi.USHORT, rffi.UCHAR])

class Signed(Type):
    def __init__(self, size=8):
        assert isinstance(size, int)
        self.align = size
        self.size = size

    def cast_to_ffitype(self):
        for rtype in signed_types:
            if self.size == rffi.sizeof(rtype):
                return clibffi.cast_type_to_ffitype(rtype)
        else:
            assert False, "undefined ffi type"

    def load(self, offset):
        for rtype in signed_types:
            if self.size == rffi.sizeof(rtype):
                return Integer(rffi.cast(rffi.LONG, rffi.cast(rffi.CArrayPtr(rtype), offset)[0]))
        else:
            assert False, "undefined ffi type"

    def store(self, offset, value):
        if not isinstance(value, Integer):
            raise Exception("cannot transform to primtype")
        for rtype in signed_types:
            if self.size == rffi.sizeof(rtype):
                pnt = rffi.cast(rffi.CArrayPtr(rtype), offset)
                pnt[0] = rffi.cast(rtype, value.value)
                break
        else:
            assert False, "undefined ffi type"

    def repr(self):
        return "<signed " + str(self.size) + ">"

class Unsigned(Type):
    def __init__(self, size=8):
        assert isinstance(size, int)
        self.align = size
        self.size = size

    def cast_to_ffitype(self):
        for rtype in unsigned_types:
            if self.size == rffi.sizeof(rtype):
                return clibffi.cast_type_to_ffitype(rtype)
        else:
            assert False, "undefined ffi type"

    def load(self, offset):
        for rtype in unsigned_types:
            if self.size == rffi.sizeof(rtype):
                return Integer(rffi.cast(rffi.LONG, rffi.cast(rffi.CArrayPtr(rtype), offset)[0]))
        else:
            assert False, "undefined ffi type"

    def store(self, offset, value):
        if not isinstance(value, Integer):
            raise Exception("cannot transform to primtype")
        for rtype in unsigned_types:
            if self.size == rffi.sizeof(rtype):
                pnt = rffi.cast(rffi.CArrayPtr(rtype), offset)
                pnt[0] = rffi.cast(rtype, value.value)
                break
        else:
            assert False, "undefined ffi type"

    def repr(self):
        return "<unsigned " + str(self.size) + ">"

# We don't have float object yet.
#class Float(Type):
#    def __init__(self, size=4):
#        self.align = size
#        self.size = size

