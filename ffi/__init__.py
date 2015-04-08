from space import *
from rpython.rlib import rdynload, objectmodel
from rpython.rtyper.lltypesystem import rffi, lltype

class Wrap(Object):
    def __init__(self, cname, ctype):
        self.cname = cname
        self.ctype = ctype

@Wrap.instantiator
def _(argv):
    cname = argument(argv, 0, String).string
    ctype = argument(argv, 1, Object)
    return Wrap(cname, ctype)

class Library(Object):
    def __init__(self, name, api, lib):
        self.name = name
        self.api = api
        self.lib = lib
        self.namespace = {}

    def getattr(self, name):
        if name in self.namespace:
            return self.namespace[name]
        cname = name
        ctype = null
        if self.api is not null:
            c = self.api.getitem(String(name))
            if isinstance(c, Wrap):
                cname = c.cname
                ctype = c.ctype
            else:
                return c
        try:
            pointer = rdynload.dlsym(self.lib, cname)
        except KeyError, e:
            raise Error("Not in the library: " + name)
        self.namespace[name] = handle = Handle(self, name, pointer, ctype)
        return handle

@Library.instantiator
def _(argv):
    if len(argv) < 1:
        raise Error("library requires at least a path name")
    name = argument(argv, 0, String)
    apispec = argv[1] if len(argv) > 1 else null
    path = rffi.str2charp(name.string)
    try:
        lib = rdynload.dlopen(path)
    except rdynload.DLOpenError, e:
        raise Error("Unable to load library: " + e.msg)
    finally:
        lltype.free(path, flavor='raw')
    return Library(name.string, apispec, lib)

class Handle(Object):
    def __init__(self, library, name, pointer, ctype):
        self.library = library
        self.name = name
        self.pointer = pointer
        self.ctype = ctype

    def call(self, argv):
        raise Error("can't cffi call yet")
#        assert isinstance(self.tp, CFunc), "not a c function"
#        return self.tp.ccall(self.pointer, argv)
#
    def repr(self):
        return "<Handle " + self.name + ' from ' + self.library.name + '>'

module = Module('ffi', {
    'library': Library.interface,
    'handle': Handle.interface,
    'wrap': Wrap.interface,
}, frozen=True)

def builtin(fn):
    module.namespace[fn.__name__] = Builtin(fn)
    return fn

#from object import Object, List, String, Symbol, Integer, BuiltinFunction, Module, true, false, null
#from systemv import *
#from api import *
#
#def pyl_cfunc(argv):
#    assert len(argv) >= 2
#    restype = argv.pop(0)
#    assert isinstance(restype, Type) or restype is null
#    for argtype in argv:
#        assert isinstance(argtype, Type)
#    return CFunc(restype, argv)
#
#def pyl_cdef(argv):
#    assert len(argv) == 2
#    handle, tp = argv
#    assert isinstance(handle, Handle)
#    assert isinstance(tp, Type)
#    handle.tp = tp
#    return handle
#
#def pyl_ptr(argv):
#    assert len(argv) == 1
#    to = argv[0]
#    assert isinstance(to, Type)
#    return Pointer(to)
#
#default_api_environment = {
#    'char': Unsigned(1),
#    'byte': Unsigned(1),
#    'sbyte': Signed(1),
#    'ubyte': Unsigned(1),
#    'short': Unsigned(2),
#    'ushort': Unsigned(2),
#    'int': Signed(4),
#    'uint': Unsigned(4),
#    'long': Signed(Pointer.size),
#    'ulong': Unsigned(Pointer.size),
#    'lllong': Signed(16),
#    'ullong': Unsigned(16),
#    'i8': Signed(1),
#    'i16': Signed(2),
#    'i32': Signed(4),
#    'i64': Signed(8),
#}
#
#module = Module("ffi", {
#    'cfunc': BuiltinFunction(pyl_cfunc, 'ffi.cfunc'),
#    'cdef': BuiltinFunction(pyl_cdef, 'ffi.cdef'),
#    'ptr': BuiltinFunction(pyl_ptr, 'ffi.ptr'),
#    'voidp': Pointer(null),
#    
##    #'char': CPrimType(rffi.CHAR, 'char'),
##    #'ccharp': CPrimPointer(rffi.CCHARP, 'ccharp'),
##    #'ccharpp': CPrimPointer(rffi.CCHARPP, 'ccharpp'),
##    'ulong': CPrimType(rffi.ULONG, 'ulong'),
#}, frozen=True)
#
#module.namespace.update(default_api_environment)
#@ffi_builtin('api')
#def ffi_api(argv):
#    assert len(argv) >= 1
#    source = argv.pop(0)
#    return APISpec(source, default_api_environment)
#
#@ffi_builtin('sizeof')
#def ffi_sizeof(argv):
#    tp = argument(argv, 0, Type)
#    if len(argv) >= 2:
#        n = argument(argv, 1, Integer)
#        return Integer(sizeof_a(tp, n.value))
#    else:
#        return Integer(sizeof(tp))
#
#@ffi_builtin('malloc')
#def ffi_malloc(argv):
#    tp = argument(argv, 0, Type)
#    if len(argv) >= 2:
#        n = argument(argv, 1, Integer)
#        sz = sizeof_a(tp, n.value)
#    else:
#        sz = sizeof(tp)
#    pointer = lltype.malloc(rffi.VOIDP.TO, sz, flavor='raw')
#    return Memory(Pointer(tp), pointer)
#
#@ffi_builtin('free')

#@builtin
#def free(argv):
#    mem = argument(argv, 0, Mem)
#    lltype.free(mem.pointer, flavor='raw')
#    mem.pointer = rffi.cast(rffi.VOIDP, 0)
#    return null
