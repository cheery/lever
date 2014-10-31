from object import Object, List, String, Symbol, Integer, BuiltinFunction, Module, true, false, null
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit_libffi, rdynload, clibffi

class CDLL(Object):
    def __init__(self, name):
        self.name = name
        self.lib = rdynload.dlopen(name)
        self.namespace = {}

    def getattr(self, name):
        if name not in self.namespace:
            pointer = rdynload.dlsym(self.lib, name)
            self.namespace[name] = cfunc = CFunc(self, name, pointer)
            return cfunc
        return self.namespace[name]

    def setattr(self, name, value):
        self.namespace[name] = value

    def repr(self):
        return '<ffi.dlopen ' + self.name + '>'

class CFunc(Object):
    def __init__(self, cdll, name, pointer):
        self.cdll = cdll
        self.name = name
        self.pointer = pointer
        self.restype = null
        self.argtypes = []
        self.argoffsets = []
        self.cif = lltype.nullptr(jit_libffi.CIF_DESCRIPTION)
        self.ready = False

    def prep_call(self):
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
            cif.exchange_args[i] = exchange_size
            exchange_size += self.argtypes[i].size
        cif.exchange_result = exchange_size
        cif.exchange_result_libffi = exchange_size
        if self.restype is null:
            exchange_size += 0
        elif self.restype:
            exchange_size += self.restype.size
        cif.exchange_size = exchange_size

        jit_libffi.jit_ffi_prep_cif(cif)
        self.cif = cif

    def invoke(self, argv):
        if not self.ready:
            self.prep_call()
            self.ready = True

        # Exchange buffer is built for every call. Filled with arguments that are passed to the function.
        argc = len(self.argtypes)
        argb = min(argc, len(argv))
        exc = lltype.malloc(rffi.CCHARP.TO, self.cif.exchange_size, flavor='raw')

        for i in range(argb):
            offset_p = rffi.ptradd(exc, self.cif.exchange_args[i])
            self.argtypes[i].store(offset_p, argv[i])

        for i in range(argb, argc):
            offset_p = rffi.ptradd(exc, self.cif.exchange_args[i])
            self.argtypes[i].store(offset_p, null)

        jit_libffi.jit_ffi_call(self.cif, self.pointer, exc)

        if self.restype is null:
            retval = null
        else:
            offset_p = rffi.ptradd(exc, self.cif.exchange_result)
            retval = self.restype.load(offset_p)
        lltype.free(exc, flavor='raw')
        return retval

    def repr(self):
        return '<c function ' + self.name + ' in ' + self.cdll.name + '>'

class CType(Object):
    def repr(self):
        return '<' + self.name + '>'

class CPrimType(CType):
    def __init__(self, ltype, name):
        self.ltype = ltype
        self.ptype = ptype = rffi.CArrayPtr(self.ltype)
        self.name = name
        self.size = rffi.sizeof(ltype)

    def load(self, offset_p):
        pnt = rffi.cast(rffi.LONGP, offset_p)
        return Integer(pnt[0])

    def store(self, offset_p, value):
        if isinstance(value, Integer):
            pnt = rffi.cast(rffi.LONGP, offset_p)
            pnt[0] = rffi.cast(rffi.LONG, value.value)
        else:
            raise Exception("cannot transform to primtype")

    def cast_to_ffitype(self):
        return clibffi.cast_type_to_ffitype(self.ltype)

class CPrimPointer(CType):
    def __init__(self, ptype, name):
        self.ptype = ptype
        self.name = name
        self.size = rffi.sizeof(ptype)

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer


def pyl_CDLL(argv):
    assert len(argv) > 0
    name = argv[0]
    assert isinstance(name, String)
    return CDLL(name.string)

def pyl_cdef(argv):
    assert len(argv) >= 2
    cfunc = argv.pop(0)
    assert isinstance(cfunc, CFunc)
    assert not cfunc.ready
    restype = argv.pop(0)
    assert isinstance(restype, CType) or restype is null
    cfunc.restype = restype
    cfunc.argtypes = []
    for arg in argv:
        assert isinstance(arg, CType)
        cfunc.argtypes.append(arg)
    return cfunc

module = Module("ffi", {
    'dlopen': BuiltinFunction(pyl_CDLL, 'ffi.dlopen'),
    'cdef': BuiltinFunction(pyl_cdef, 'ffi.cdef'),
    #'char': CPrimType(rffi.CHAR, 'char'),
    #'ccharp': CPrimPointer(rffi.CCHARP, 'ccharp'),
    #'ccharpp': CPrimPointer(rffi.CCHARPP, 'ccharpp'),
    'long': CPrimType(rffi.LONG, 'long'),
    'ulong': CPrimType(rffi.ULONG, 'ulong'),
    #'voidp': CPrimPointer(rffi.VOIDP, 'voidp'),
}, frozen=True)
