from object import Object, List, String, Symbol, Integer, BuiltinFunction, Module, true, false, null
from rpython.rlib import rdynload
from systemv import *
from api import *

#def align(x, a):
#    return x + (a - x % a) % a
#
#def sizeof(tp):
#    assert tp.size is not None, "cannot determine size of opaque type"
#    return tp.size

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

module = Module("ffi", {
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

default_api_environment = {
    'char': Signed(1),
    'byte': Unsigned(1),
    'int': Signed(4),
    'uint': Unsigned(4),
    'long': Signed(Pointer.size),
    'ulong': Unsigned(Pointer.size),
}

@ffi_builtin('dlopen')
def pyl_dlopen(argv):
    assert len(argv) > 0
    name = argv[0]
    assert isinstance(name, String)
    apispec = null
    if len(argv) > 1:
        apispec = argv[1]
    return Library(name.string, apispec)
