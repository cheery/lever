from object import Object, Integer, null
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit_libffi, clibffi, unroll

def align(x, a):
    return x + (a - x % a) % a

def sizeof(tp):
    assert isinstance(tp, Type)
    assert tp.size > 0 and tp.align > 0, "cannot determine size of opaque type"
    return tp.size

def sizeof_a(tp, n):
    assert isinstance(tp, Type)
    assert tp.size > 0 and tp.align > 0, "cannot determine size of opaque type"
    if tp.parameter is not None:
        return tp.size + sizeof(tp.parameter)*n
    else:
        return tp.size * n

class Type(Object):
    parameter = None
    size = 0
    align = 0

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


#class Float(Type):
#    def __init__(self, size=4):
#        self.align = size
#        self.size = size

class Pointer(Type):
    size = rffi.sizeof(rffi.VOIDP)
    def __init__(self, to):
        self.to = to
        self.align = self.size

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset):
        return Memory(self.to, rffi.cast(rffi.VOIDPP, offset)[0])

    def store(self, offset, value):
        # type checking here will most likely reduce some cringes, so add some later.
        if not isinstance(value, Memory):
            raise Exception("cannot transform value to memory")
        pnt = rffi.cast(rffi.VOIDPP, offset)
        pnt[0] = value.pointer

    def repr(self):
        return "<* "+self.to.repr()+">"

class CFunc(Type):
    def __init__(self, restype, argtypes):
        self.restype = restype
        self.argtypes = argtypes
        self.size = rffi.sizeof(rffi.VOIDP)
        self.align = self.size
        self.cif = lltype.nullptr(jit_libffi.CIF_DESCRIPTION)
        self.notready = True

    def prep_cif(self):
        # The cif is initialized with the stuff needed to call the function
        argc = len(self.argtypes)

        cif = lltype.malloc(jit_libffi.CIF_DESCRIPTION, argc, flavor='raw')
        # atypes points to an array of ffi_type pointers
        cif.abi = clibffi.FFI_DEFAULT_ABI
        cif.atypes = lltype.malloc(clibffi.FFI_TYPE_PP.TO, argc, flavor='raw')
        for i in range(argc):
            cif.atypes[i] = self.argtypes[i].cast_to_ffitype()
        cif.nargs = argc
        if self.restype is null:
            cif.rtype = clibffi.ffi_type_void
        else:
            cif.rtype = self.restype.cast_to_ffitype()

        exchange_size = argc * rffi.sizeof(rffi.VOIDPP)
        for i in range(argc):
            argtype = self.argtypes[i]
            exchange_size = align(exchange_size, argtype.align)
            cif.exchange_args[i] = exchange_size
            exchange_size += sizeof(argtype)
        cif.exchange_result = exchange_size
        cif.exchange_result_libffi = exchange_size
        if self.restype is null:
            exchange_size += 0
        elif self.restype:
            exchange_size += sizeof(self.restype)
        cif.exchange_size = exchange_size

        jit_libffi.jit_ffi_prep_cif(cif)
        self.cif = cif

    def ccall(self, pointer, argv):
        if self.notready:
            self.prep_cif()
            self.notready = False
        cif = self.cif
        # Exchange buffer is built for every call. Filled with arguments that are passed to the function.
        argc = len(argv)
        assert argc == len(self.argtypes), "cfunc arity must match with the call"
        exc = lltype.malloc(rffi.VOIDP.TO, cif.exchange_size, flavor='raw')
        for i in range(argc):
            offset = rffi.ptradd(exc, cif.exchange_args[i])
            self.argtypes[i].store(offset, argv[i])
        jit_libffi.jit_ffi_call(cif, pointer, exc)
        retval = null
        if isinstance(self.restype, Type):
            offset = rffi.ptradd(exc, cif.exchange_result)
            retval = self.restype.load(offset)
        lltype.free(exc, flavor='raw')
        return retval

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset):
        return Memory(self, rffi.cast(rffi.VOIDPP, offset)[0])

    def store(self, offset, value):
        # type checking here will most likely reduce some cringes, so add some later.
        if not isinstance(value, Memory):
            raise Exception("cannot transform value to memory")
        pnt = rffi.cast(rffi.VOIDPP, offset)
        pnt[0] = value.pointer

    def repr(self):
        string = '<cfunc ' + self.restype.repr()
        for argtype in self.argtypes:
            string += ' ' + argtype.repr()
        return string + '>'

class Struct(Type):
    def __init__(self, fields=None):
        self.offsets = []
        self.namespace = {}
        self.size = 0
        self.align = 0
        self.fields = None
        if fields is not None:
            self.define(fields)

    def define(self, fields):
        assert self.fields is None, "struct can be defined only once"
        self.fields = fields
        self.align = 1

        offset = 0
        for name, tp in fields:
            assert not self.parameter, "parametric field in middle of a structure"
            if tp.parameter:
                self.parameter = tp.parameter
            offset = align(offset, tp.align)
            self.offsets.append(offset)
            self.align = max(self.align, tp.align)
            self.namespace[name] = (offset, tp)
            offset += sizeof(tp)
        self.size = align(offset, self.align)

    def repr(self):
        names = []
        for name, tp in self.fields:
            names.append('.' + name)
        return '<struct ' + ' '.join(names) + '>'

class Union(Type):
    def __init__(self, fields):
        self.fields = fields
        self.namespace = {}
        self.align = 1
        self.size = 0
        for name, tp in fields:
            self.align = max(self.align, tp.align)
            self.size = max(self.size, sizeof(tp))
            assert not tp.parameter, "parametric field in an union"
            self.namespace[name] = (0, tp)

    def repr(self):
        names = []
        for name, tp in self.fields:
            names.append('.' + name)
        return '<union ' + ' '.join(names) + '>'

class Array(Type):
    def __init__(self, tp, length=0):
        self.tp = tp
        assert not tp.parameter, "parametric field in an array"
        if length == 0:
            self.parameter = self
            self.size = 0
        else:
            self.size = sizeof(tp) * int(length)
        self.align = tp.align

    def repr(self):
        return '<array ' + self.tp.repr() + '>'

class Memory(Object):
    def __init__(self, tp, pointer):
        self.tp = tp
        self.pointer = pointer

    def getattr(self, name):
        if isinstance(self.tp, Pointer):
            to = self.tp.to
        else:
            to = None
        if isinstance(to, Struct) or isinstance(to, Union):
            if not name in to.namespace:
                raise Exception("object does not contain field ." + name)
            offset, tp = to.namespace[name]
            pointer = rffi.ptradd(self.pointer, offset)
            if isinstance(tp, Struct) or isinstance(tp, Union): # or isinstance(tp, Array):
                return Memory(Pointer(tp), pointer)
            elif isinstance(tp, Signed) or isinstance(tp, Unsigned):
                return tp.load(pointer)
            else:
                raise Exception("no load supported for all objects")
        else:
            raise Exception("cannot attribute access other objects than structs and unions")

    def invoke(self, argv):
        if isinstance(self.tp, CFunc):
            return self.tp.ccall(self.pointer, argv)
        raise Exception("cannot call non-cfunc")

    def repr(self):
        name = self.tp.repr()
        if self.tp is null:
            name = ''
        return "<" + hex(rffi.cast(rffi.LONG, self.pointer)) + " " + name + ">"
