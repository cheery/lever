from rpython.rlib import jit_libffi, clibffi, unroll
from rpython.rtyper.lltypesystem import rffi, lltype
from space import unwind, LTypeError, Object, Integer, Float, to_float, to_int, String
# Simple, platform independent concepts are put up
# here, so they won't take space elsewhere.

class Type(Object):
    parameter = None # Some of the C types are parametric
                     # it's ok.
    size = 0  # These fields remain zero if it's an
    align = 0 # opaque type.

    def cast_to_ffitype(self):
        raise unwind(LTypeError(u".cast_to_ffitype method missing"))

    def load(self, offset, copy):
        raise unwind(LTypeError(u".load method missing"))

    def store(self, pool, offset, value):
        raise unwind(LTypeError(u".store method missing"))

    def typecheck(self, other):
        return self is other

    def on_getattr(self, mem, name):
        if name == u"to":
            return self.load(mem.pointer, False)
        if name == u"str" and self.size == 1:
            s = rffi.charp2str(rffi.cast(rffi.CCHARP, mem.pointer))
            return String(s.decode('utf-8'))
        raise Object.getattr(mem, name)

    def on_setattr(self, mem, name, value):
        if name == u"to":
            return self.store(mem.pool, mem.pointer, value)
        raise Object.setattr(mem, name, value)

# Many systems are sensitive to memory alignment
def align(x, a):
    return x + (a - x % a) % a

def sizeof(tp):
    assert isinstance(tp, Type)
    if tp.size == 0 or tp.align == 0:
        raise unwind(LTypeError(u"cannot determine size of opaque type"))
    return tp.size

# This is something rpython's allocator is doing, and
# it looks nice enough. Allocations are treated as arrays,
# in parametric records the parameter is treated as an array.
def sizeof_a(tp, n):
    assert isinstance(tp, Type)
    if tp.size == 0 or tp.align == 0:
        raise unwind(LTypeError(u"cannot determine size of opaque type"))
    if tp.parameter is not None:
        return tp.size + sizeof(tp.parameter)*n
    else:
        return tp.size * n

signed_types = unroll.unrolling_iterable([rffi.LONG, rffi.INT, rffi.SHORT, rffi.CHAR, rffi.LONGLONG])
unsigned_types = unroll.unrolling_iterable([rffi.ULONG, rffi.UINT, rffi.USHORT, rffi.UCHAR, rffi.ULONGLONG])
floating_types = unroll.unrolling_iterable([rffi.FLOAT, rffi.DOUBLE])

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
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))

    def load(self, offset, copy):
        for rtype in signed_types:
            if self.size == rffi.sizeof(rtype):
                return Integer(rffi.cast(rffi.LONG, rffi.cast(rffi.CArrayPtr(rtype), offset)[0]))
        else:
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))

    def store(self, pool, offset, value):
        for rtype in signed_types:
            if self.size == rffi.sizeof(rtype):
                pnt = rffi.cast(rffi.CArrayPtr(rtype), offset)
                pnt[0] = rffi.cast(rtype, to_int(value))
                break
        else:
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))
        return value

    def typecheck(self, other):
        if isinstance(other, Signed) and self.size == other.size:
            return True
        if isinstance(other, Unsigned) and self.size == other.size:
            return True
        return False

    def repr(self):
        return u"<signed %d>" % self.size

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
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))

    def load(self, offset, copy):
        for rtype in unsigned_types:
            if self.size == rffi.sizeof(rtype):
                return Integer(rffi.cast(rffi.LONG, rffi.cast(rffi.CArrayPtr(rtype), offset)[0]))
        else:
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))

    def store(self, pool, offset, value):
        for rtype in unsigned_types:
            if self.size == rffi.sizeof(rtype):
                pnt = rffi.cast(rffi.CArrayPtr(rtype), offset)
                pnt[0] = rffi.cast(rtype, to_int(value))
                break
        else:
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))
        return value

    def repr(self):
        return u"<unsigned %d>" % self.size

    def typecheck(self, other):
        if isinstance(other, Signed) and self.size == other.size:
            return True
        if isinstance(other, Unsigned) and self.size == other.size:
            return True
        return False

class Floating(Type):
    def __init__(self, size=4):
        self.align = size
        self.size = size

    def cast_to_ffitype(self):
        for rtype in floating_types:
            if self.size == rffi.sizeof(rtype):
                return clibffi.cast_type_to_ffitype(rtype)
        else:
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))

    def load(self, offset, copy):
        for rtype in floating_types:
            if self.size == rffi.sizeof(rtype):
                return Float(rffi.cast(rffi.DOUBLE, rffi.cast(rffi.CArrayPtr(rtype), offset)[0]))
        else:
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))

    def store(self, pool, offset, value):
        number = to_float(value)
        for rtype in floating_types:
            if self.size == rffi.sizeof(rtype):
                pnt = rffi.cast(rffi.CArrayPtr(rtype), offset)
                pnt[0] = rffi.cast(rtype, number)
                break
        else:
            raise unwind(LTypeError(u"undefined ffi type: %s" % self.repr()))
        return value

    def repr(self):
        return u"<floating %d>" % self.size

    def typecheck(self, other):
        if isinstance(other, Floating) and self.size == other.size:
            return True
        return False

# The idea here is that you can shadow the ffi types
# With your own classes or objects, changing their
# behavior.
class Shadow(Type):
    def __init__(self, basetype, obj):
        self.basetype = basetype
        self.parameter = basetype.parameter
        self.size = basetype.size
        self.align = basetype.align
        self.obj = obj

    def cast_to_ffitype(self):
        return self.basetype.cast_to_ffitype()

    def load(self, offset, copy):
        value = self.basetype.load(offset, copy)
        return self.obj.callattr(u"load", [value])

    def store(self, pool, offset, value):
        value = self.obj.callattr(u"store", [value])
        return self.basetype.store(pool, offset, value)

    def on_getattr(self, mem, name):
        return self.basetype.on_getattr(mem, name)

    def on_setattr(self, mem, name, value):
        return self.basetype.on_setattr(mem, name, value)

def to_type(obj):
    if isinstance(obj, Type):
        return obj
    return Shadow(to_type(obj.getattr(u"shadow")), obj)
