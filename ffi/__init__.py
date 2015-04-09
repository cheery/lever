from rpython.rlib import rdynload, objectmodel
from rpython.rtyper.lltypesystem import rffi, lltype
from simple import Type
from space import *
import simple
import systemv

class Wrap(Object):
    def __init__(self, cname, ctype):
        self.cname = cname
        self.ctype = ctype

@Wrap.instantiator
@signature(String, Object)
def _(cname, ctype):
    return Wrap(cname.string, ctype)

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
        if isinstance(self.ctype, systemv.CFunc):
            return self.ctype.ccall(self.pointer, argv)
        raise Error("cannot call " + self.ctype.repr())

    def repr(self):
        return "<Handle " + self.name + ' from ' + self.library.name + '>'

module = Module('ffi', {
    'array': systemv.Array.interface,
    'cfunc': systemv.CFunc.interface,
    'handle': Handle.interface,
    'library': Library.interface,
    'mem': systemv.Mem.interface,
    'pointer': systemv.Pointer.interface,
    'signed': simple.Signed.interface,
    'struct': systemv.Struct.interface,
    'union': systemv.Union.interface,
    'unsigned': simple.Unsigned.interface,
    'voidp': systemv.Pointer(null),
    'wrap': Wrap.interface,
}, frozen=True)
module.namespace.update(systemv.types)

def builtin(fn):
    module.namespace[fn.__name__] = Builtin(fn)
    return fn

@builtin
@signature(Object, Type)
def cast(obj, ctype):
    if isinstance(obj, Handle):
        return Handle(obj.library, obj.name, obj.pointer, ctype)
    if isinstance(obj, systemv.Mem):
        return systemv.Mem(ctype, obj.pointer)
    raise Error("Can cast memory locations only")

# This didn't belong here to start with.. It will soon get
# its own module
#@ffi_builtin('api')
#def ffi_api(argv):
#    assert len(argv) >= 1
#    source = argv.pop(0)
#    return APISpec(source, default_api_environment)

@builtin
def sizeof(argv):
    ctype = argument(argv, 0, Type)
    if len(argv) >= 2:
        n = argument(argv, 1, Integer)
        size = simple.sizeof_a(ctype, n.value)
    else:
        size = simple.sizeof(ctype)
    return Integer(size)

@builtin
def malloc(argv):
    ctype = argument(argv, 0, Type)
    if len(argv) >= 2:
        n = argument(argv, 1, Integer)
        size = simple.sizeof_a(ctype, n.value)
    else:
        size = simple.sizeof(ctype)
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    return systemv.Mem(systemv.Pointer(ctype), pointer)

@builtin
def free(argv):
    mem = argument(argv, 0, systemv.Mem)
    lltype.free(mem.pointer, flavor='raw')
    mem.pointer = rffi.cast(rffi.VOIDP, 0)
    return null
