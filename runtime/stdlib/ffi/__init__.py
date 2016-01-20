from rpython.rlib import rdynload, objectmodel
from rpython.rtyper.lltypesystem import rffi, lltype
from simple import Type
from space import *
from systemv import Mem, Pointer, CFunc, Struct, Union, Array
import simple
import systemv

class Wrap(Object):
    def __init__(self, cname, ctype):
        self.cname = cname
        self.ctype = ctype

    def repr(self):
        return u"<wrap %s %s>" % (self.cname, self.ctype.repr())

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
        cname = name.encode('utf-8')
        ctype = null
        if self.api is not null:
            c = self.api.getitem(String(name))
            if isinstance(c, Wrap):
                cname = c.cname.encode('utf-8')
                ctype = c.ctype
            else:
                return c
        try:
            pointer = rdynload.dlsym(self.lib, cname)
        except KeyError, e:
            raise Error(u"Not in the library: " + name)
        self.namespace[name] = handle = Handle(self, name, pointer, ctype)
        return handle

@Library.instantiator
def _(argv):
    if len(argv) < 1:
        raise Error(u"library requires at least a path name")
    name = argument(argv, 0, String)
    apispec = argv[1] if len(argv) > 1 else null
    path = rffi.str2charp(as_cstring(name))
    try:
        lib = rdynload.dlopen(path)
    except rdynload.DLOpenError, e:
        raise Error(u"Unable to load library: " + name.string)# + e.msg.decode('utf-8'))
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
        if isinstance(self.ctype, CFunc):
            return self.ctype.ccall(self.pointer, argv)
        raise Error(u"cannot call " + self.ctype.repr())

    def repr(self):
        return u"<handle %s from %s>" % (self.name, self.library.name)

module = Module(u'ffi', {
    u'array': systemv.Array.interface,
    u'cfunc': CFunc.interface,
    u'handle': Handle.interface,
    u'library': Library.interface,
    u'mem': Mem.interface,
    u'pointer': systemv.Pointer.interface,
    u'signed': simple.Signed.interface,
    u'struct': systemv.Struct.interface,
    u'union': systemv.Union.interface,
    u'unsigned': simple.Unsigned.interface,
    u'voidp': systemv.Pointer(null),
    u'wrap': Wrap.interface,
}, frozen=True)

for name in systemv.types:
    module.setattr_force(name, systemv.types[name])

def builtin(fn):
    module.setattr_force(fn.__name__.decode('utf-8'), Builtin(fn))
    return fn

@builtin
@signature(Object, Type)
def cast(obj, ctype):
    if isinstance(obj, Handle):
        return Handle(obj.library, obj.name, obj.pointer, ctype)
    if isinstance(obj, Mem):
        return Mem(ctype, obj.pointer)
    if isinstance(obj, Integer) and isinstance(ctype, Pointer):
        return Mem(ctype, rffi.cast(rffi.VOIDP, obj.value))

    raise Error(u"Can cast memory locations only")

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
        n = argument(argv, 1, Integer).value
        size = simple.sizeof_a(ctype, n)
    else:
        n = 1
        size = simple.sizeof(ctype)
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    return Mem(systemv.Pointer(ctype), pointer, n)

@builtin
def automem(argv):
    ctype = argument(argv, 0, Type)
    if len(argv) >= 2:
        n = argument(argv, 1, Integer).value
        size = simple.sizeof_a(ctype, n)
    else:
        n = 1
        size = simple.sizeof(ctype)
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    return systemv.AutoMem(systemv.Pointer(ctype), pointer, n)

@builtin
def free(argv):
    mem = argument(argv, 0, Mem)
    lltype.free(mem.pointer, flavor='raw')
    mem.pointer = rffi.cast(rffi.VOIDP, 0)
    return null

c_ubytep = systemv.Pointer(systemv.types[u"ubyte"])

@builtin
def ref(argv):
    mem = argument(argv, 0, Object)
    if isinstance(mem, Mem):
        size = simple.sizeof(mem.ctype)
        ctype = mem.ctype
    elif isinstance(mem, Uint8Array):
        size = rffi.sizeof(rffi.VOIDP)
        ctype = c_ubytep
    else:
        raise Error(u"expected object that can be converted to c-object")
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    result = systemv.AutoMem(systemv.Pointer(ctype), pointer, 1)
    ctype.store(pointer, mem)
    return result
