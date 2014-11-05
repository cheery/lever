from object import Object, List, String, Symbol, Integer, BuiltinFunction, Module, true, false, null
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import rdynload, objectmodel
from systemv import *
from api import *

class Library(Object):
    def __init__(self, name, apispec=null):
        self.name = name
        self.lib = rdynload.dlopen(name)
        self.namespace = {}
        self.apispec = apispec

    def getattr(self, name):
        if name not in self.namespace:
            if isinstance(self.apispec, APISpec):
                tp = self.apispec.resolve(name)
                if tp is null:
                    raise Exception("cannot resolve typespec of name:" + name)
                if not isinstance(tp, Interface):
                    return tp
                sym_name = tp.name
                tp = tp.tp
            else:
                sym_name = name
                tp = null
            pointer = rdynload.dlsym(self.lib, sym_name)
            self.namespace[name] = cfunc = Handle(self, name, pointer)
            cfunc.tp = tp
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
        assert isinstance(self.tp, CFunc), "not a c function"
        return self.tp.ccall(self.pointer, argv)

    def repr(self):
        return '<handle ' + self.name + ' from ' + self.lib.name + '>'

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

default_api_environment = {
    'char': Unsigned(1),
    'byte': Unsigned(1),
    'sbyte': Signed(1),
    'short': Unsigned(2),
    'ushort': Unsigned(2),
    'int': Signed(4),
    'uint': Unsigned(4),
    'long': Signed(Pointer.size),
    'ulong': Unsigned(Pointer.size),
}

module = Module("ffi", {
    'cfunc': BuiltinFunction(pyl_cfunc, 'ffi.cfunc'),
    'cdef': BuiltinFunction(pyl_cdef, 'ffi.cdef'),
    'ptr': BuiltinFunction(pyl_ptr, 'ffi.ptr'),
    'voidp': Pointer(null),
    
#    #'char': CPrimType(rffi.CHAR, 'char'),
#    #'ccharp': CPrimPointer(rffi.CCHARP, 'ccharp'),
#    #'ccharpp': CPrimPointer(rffi.CCHARPP, 'ccharpp'),
#    'ulong': CPrimType(rffi.ULONG, 'ulong'),
}, frozen=True)

module.namespace.update(default_api_environment)

def ffi_builtin(name):
    def _impl(fn):
        module.namespace[name] = BuiltinFunction(fn, 'ffi.' + name)
        return fn
    return _impl

@ffi_builtin('api')
def ffi_api(argv):
    assert len(argv) >= 1
    source = argv.pop(0)
    return APISpec(source, default_api_environment)

@ffi_builtin('sizeof')
def ffi_sizeof(argv):
    tp = argument(argv, 0, Type)
    if len(argv) >= 2:
        n = argument(argv, 1, Integer)
        return Integer(sizeof_a(tp, n.value))
    else:
        return Integer(sizeof(tp))

@ffi_builtin('malloc')
def ffi_malloc(argv):
    tp = argument(argv, 0, Type)
    if len(argv) >= 2:
        n = argument(argv, 1, Integer)
        sz = sizeof_a(tp, n.value)
    else:
        sz = sizeof(tp)
    pointer = lltype.malloc(rffi.VOIDP.TO, sz, flavor='raw')
    return Memory(Pointer(tp), pointer)

@ffi_builtin('free')
def ffi_free(argv):
    mem = argument(argv, 0, Memory)
    lltype.free(mem.pointer, flavor='raw')
    mem.pointer = rffi.cast(rffi.VOIDP, 0)
    return null

@objectmodel.specialize.arg(1, 2)
def argument(argv, i, tp):
    if i < len(argv):
        v = argv[i]
    else:
        v = null
    if not isinstance(v, tp):
        raise Exception("expected " + tp.__name__ + " got " + v.repr())
    return v

@ffi_builtin('dlopen')
def pyl_dlopen(argv):
    assert len(argv) > 0
    name = argv[0]
    assert isinstance(name, String)
    apispec = null
    if len(argv) > 1:
        apispec = argv[1]
    return Library(name.string, apispec)
