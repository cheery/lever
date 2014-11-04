from object import Object, Integer, null
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit_libffi, clibffi

def align(x, a):
    return x + (a - x % a) % a

def sizeof(tp):
    assert tp.size > 0 and tp.align > 0, "cannot determine size of opaque type"
    return tp.size

class Type(Object):
    parameter = None
    size = 0
    align = 0

class Signed(Type):
    def __init__(self, size=8):
        self.align = size
        self.size = size

    def cast_to_ffitype(self):
        if self.size == rffi.sizeof(rffi.LONG):
            return clibffi.cast_type_to_ffitype(rffi.LONG)
        assert False, "undefined ffi type"

    def load(self, offset):
        if self.size == rffi.sizeof(rffi.LONG):
            return Integer(rffi.cast(rffi.LONGP, offset)[0])
        assert False, "undefined ffi type"

    def store(self, offset, value):
        if not isinstance(value, Integer):
            raise Exception("cannot transform to primtype")
        if self.size == rffi.sizeof(rffi.LONG):
            pnt = rffi.cast(rffi.LONGP, offset)
            pnt[0] = rffi.cast(rffi.LONG, value.value)
        else:
            assert False, "undefined ffi type"

    def repr(self):
        return "<signed>"
        #return "<signed "+str(8*self.size)+">"

class Unsigned(Type):
    def __init__(self, size=8):
        self.align = size
        self.size = size

    def cast_to_ffitype(self):
        if self.size == rffi.sizeof(rffi.ULONG):
            return clibffi.cast_type_to_ffitype(rffi.ULONG)
        assert False, "undefined ffi type"

    def load(self, offset):
        if self.size == rffi.sizeof(rffi.ULONG):
            return Integer(rffi.cast(rffi.ULONGP, offset)[0])
        assert False, "undefined ffi type"

    def store(self, offset, value):
        if not isinstance(value, Integer):
            raise Exception("cannot transform to primtype")
        if self.size == rffi.sizeof(rffi.ULONG):
            pnt = rffi.cast(rffi.ULONGP, offset)
            pnt[0] = rffi.cast(rffi.ULONG, value.value)
        else:
            assert False, "undefined ffi type"

    def repr(self):
        return "<signed "+str(8*self.size)+">"


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
        return Memory(self.to, rffi.cast(rffi.VOIDP, offset)[0])

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
        exc = lltype.malloc(rffi.CCHARP.TO, cif.exchange_size, flavor='raw')
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

    def repr(self):
        string = '<cfunc ' + self.restype.repr()
        for argtype in self.argtypes:
            string += ' ' + argtype.repr()
        return string + '>'

class Struct(Type):
    def __init__(self, fields=None):
        if fields is None:
            self.fields = None
            self.size = 0
            self.align = 0
        else:
            self.define(fields)

    def define(self, fields):
        assert self.fields is None, "struct can be defined only once"
        self.fields = fields
        self.offsets = []
        self.align = 1

        offset = 0
        for name, tp in fields:
            assert not self.parameter, "parametric field in middle of a structure"
            if tp.parameter:
                self.parameter = tp.parameter
            offset = align(offset, tp.align)
            self.offsets.append((offset, name, tp))
            self.align = max(self.align, tp.align)
            offset += sizeof(tp)
        self.size = align(offset, self.align)

    def repr(self):
        return '<struct>'

class Union(Type):
    def __init__(self, fields):
        self.fields = fields
        self.align = 1
        self.size = 0
        for name, tp in fields:
            self.align = max(self.align, tp.align)
            self.size = max(self.size, sizeof(tp.size))
            assert not tp.parameter, "parametric field in an union"

    def repr(self):
        return '<union>'

class Array(Type):
    def __init__(self, tp, length=None):
        self.tp = tp
        assert not tp.parameter, "parametric field in an array"
        if length is None:
            self.parameter = self
            self.size = 0
        else:
            self.size = sizeof(tp) * length
        self.align = tp.align

    def repr(self):
        return '<array ' + self.tp.repr() + '>'

class Memory(Object):
    def __init__(self, tp, pointer):
        self.tp = tp
        self.pointer = rffi.cast(rffi.VOIDP, pointer)

    def invoke(self, argv):
        if isinstance(self.tp, CFunc):
            return self.tp.ccall(self.pointer, argv)
        raise Exception("cannot call non-cfunc")

    def repr(self):
        name = self.tp.repr()
        if self.tp is null:
            name = 'memory'
        return "<" + name + " " + str(self.pointer) + ">"
