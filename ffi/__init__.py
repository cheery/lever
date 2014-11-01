from object import Object, List, String, Symbol, Integer, BuiltinFunction, Module, true, false, null
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit_libffi, rdynload, clibffi

def align(x, a):
    return x + (a - x % a) % a

def sizeof(tp):
    assert tp.size is not None, "cannot determine size of opaque type"
    return tp.size

class Library(Object):
    def __init__(self, name):
        self.name = name
        self.lib = rdynload.dlopen(name)
        self.namespace = {}

    def getattr(self, name):
        if name not in self.namespace:
            pointer = rdynload.dlsym(self.lib, name)
            self.namespace[name] = cfunc = Handle(self, name, pointer)
            return cfunc
        return self.namespace[name]

    def setattr(self, name, value):
        self.namespace[name] = value

    def repr(self):
        return '<ffi.dlopen ' + self.name + '>'

class Handle(Object):
    def __init__(self, lib, name, pointer):
        self.lib = lib
        self.name = name
        self.pointer = pointer
        self.tp = null

    def invoke(self, argv):
        assert isinstance(self.tp, CFunc)
        cfunc = self.tp
        if cfunc.notready:
            cfunc.prep_cif()
            cfunc.notready = False
        cif = cfunc.cif
        # Exchange buffer is built for every call. Filled with arguments that are passed to the function.
        argc = len(argv)
        assert argc == len(cfunc.argtypes), "cfunc arity must match with the call"
        exc = lltype.malloc(rffi.CCHARP.TO, cif.exchange_size, flavor='raw')
        for i in range(argc):
            offset = rffi.ptradd(exc, cif.exchange_args[i])
            cfunc.argtypes[i].store(offset, argv[i])
        jit_libffi.jit_ffi_call(cif, self.pointer, exc)
        retval = null
        if isinstance(cfunc.restype, Type):
            offset = rffi.ptradd(exc, cif.exchange_result)
            retval = cfunc.restype.load(offset)
        lltype.free(exc, flavor='raw')
        return retval

    def repr(self):
        return '<handle ' + self.name + ' from ' + self.lib.name + '>'

class Type(Object):
    pass

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

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def repr(self):
        string = '<cfunc ' + self.restype.repr()
        for argtype in self.argtypes:
            string += ' ' + argtype.repr()
        return string + '>'

class Signed(Type):
    def __init__(self, size):
        self.size = size
        self.align = self.size

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
        return "<signed "+str(8*self.size)+">"

class Pointer(Type):
    def __init__(self, to):
        self.to = to
        self.size = rffi.sizeof(rffi.VOIDP)
        self.align = self.size

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset):
        return Memory(self.to, rffi.cast(rffi.VOIDP, offset)[0])

    def store(self, offset, value):
        # type checking here will most likely reduce some cringes, so add some later.
        if not isinstance(value, Memory):
            raise Exception("cannot transform to memory")
        pnt = rffi.cast(rffi.VOIDP, offset)
        pnt[0] = value.pointer

    def repr(self):
        return "<* "+self.to.repr()+">"

class Memory(Object):
    def __init__(self, tp, pointer):
        self.tp = tp
        self.pointer = pointer

    def repr(self):
        name = self.tp.repr()
        if self.tp is null:
            name = 'memory'
        return "<" + name + " " + str(self.pointer) + ">"

def pyl_dlopen(argv):
    assert len(argv) > 0
    name = argv[0]
    assert isinstance(name, String)
    return Library(name.string)

def pyl_cfunc(argv):
    assert len(argv) >= 2
    restype = argv.pop(0)
    assert isinstance(restype, Type) or restype is null
    for argtype in argv:
        assert isinstance(argtype, Type)
    return CFunc(restype, argv)

def pyl_cdef(argv):
    assert len(argv) == 2
    handle, tp = argv
    assert isinstance(handle, Handle)
    assert isinstance(tp, Type)
    handle.tp = tp
    return handle

def pyl_ptr(argv):
    assert len(argv) == 1
    to = argv[0]
    assert isinstance(to, Type)
    return Pointer(to)

module = Module("ffi", {
    'dlopen': BuiltinFunction(pyl_dlopen, 'ffi.dlopen'),
    'cfunc': BuiltinFunction(pyl_cfunc, 'ffi.cfunc'),
    'cdef': BuiltinFunction(pyl_cdef, 'ffi.cdef'),
    'ptr': BuiltinFunction(pyl_ptr, 'ffi.ptr'),
    'long': Signed(rffi.sizeof(rffi.LONG)),
    'voidp': Pointer(null),
    
#    #'char': CPrimType(rffi.CHAR, 'char'),
#    #'ccharp': CPrimPointer(rffi.CCHARP, 'ccharp'),
#    #'ccharpp': CPrimPointer(rffi.CCHARPP, 'ccharpp'),
#    'ulong': CPrimType(rffi.ULONG, 'ulong'),
}, frozen=True)
