from rpython.rlib import rdynload, objectmodel
from rpython.rtyper.lltypesystem import rffi, lltype
from simple import Type, to_type
from space import *
from systemv import Mem, Pointer, CFunc, Struct, Union, Array
from bitmask import Bitmask
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
            return Object.getattr(self, name)
        self.namespace[name] = handle = Handle(self, name, pointer, ctype)
        return handle

@Library.instantiator
@signature(String, Object, optional=1)
def _(name, apispec):
    apispec = null if apispec is None else apispec
    path = rffi.str2charp(as_cstring(name))
    try:
        lib = rdynload.dlopen(path)
    except rdynload.DLOpenError, e:
        raise unwind(LLoadError(name))
        #raise OldError(u"Unable to load library: " + name.string)# + e.msg.decode('utf-8'))
    finally:
        lltype.free(path, flavor='raw')
    return Library(name.string, apispec, lib)

class LLoadError(LException):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return u"Unable to load library: %s" % self.name.repr()

class Handle(Object):
    def __init__(self, library, name, pointer, ctype):
        self.library = library
        self.name = name
        self.pointer = pointer
        self.ctype = ctype

    def call(self, argv):
        if isinstance(self.ctype, CFunc):
            return self.ctype.ccall(self.pointer, argv)
        return Object.call(self, argv)

    def repr(self):
        return u"<handle %s from %s>" % (self.name, self.library.name)

module = Module(u'ffi', {
    u'array': systemv.Array.interface,
    u'bitmask': Bitmask.interface,
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
    u'pool': systemv.Pool.interface,
}, frozen=True)

for name in systemv.types:
    module.setattr_force(name, systemv.types[name])

def builtin(fn):
    module.setattr_force(fn.__name__.decode('utf-8'), Builtin(fn))
    return fn

@builtin
@signature(Object, Object)
def cast(obj, ctype):
    ctype = to_type(ctype)
    if isinstance(obj, Handle):
        return Handle(obj.library, obj.name, obj.pointer, ctype)
    if isinstance(obj, Mem):
        return Mem(ctype, obj.pointer)
    if isinstance(obj, Uint8Array):
        return Mem(ctype, rffi.cast(rffi.VOIDP, obj.uint8data))
    if isinstance(obj, Integer) and isinstance(ctype, Pointer):
        return Mem(ctype, rffi.cast(rffi.VOIDP, obj.value))
    raise unwind(LTypeError(u"Can cast memory locations only"))

@builtin
@signature(Object, Integer, optional=1)
def sizeof(ctype, count):
    ctype = to_type(ctype)
    if count:
        size = simple.sizeof_a(ctype, count.value)
    else:
        size = simple.sizeof(ctype)
    return Integer(size)

@builtin
@signature(Object, Integer, Boolean, optional=2)
def malloc(ctype, count, clear):
    ctype = to_type(ctype)
    if count:
        n = count.value
        size = simple.sizeof_a(ctype, n)
    else:
        n = 1
        size = simple.sizeof(ctype)
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    if is_true(clear):
        rffi.c_memset(pointer, 0, size)
    return Mem(systemv.Pointer(ctype), pointer, n)

@builtin
@signature(Object, Integer, Boolean, optional=2)
def automem(ctype, count, clear):
    ctype = to_type(ctype)
    if count:
        n = count.value
        size = simple.sizeof_a(ctype, n)
    else:
        n = 1
        size = simple.sizeof(ctype)
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    if is_true(clear):
        rffi.c_memset(pointer, 0, size)
    return systemv.AutoMem(systemv.Pointer(ctype), pointer, n)

@builtin
@signature(Mem)
def free(mem):
    #mem = argument(argv, 0, Mem)
    lltype.free(mem.pointer, flavor='raw')
    mem.pointer = rffi.cast(rffi.VOIDP, 0)
    return null

@builtin
@signature(Mem, Integer, Integer)
def memset(mem, num, count):
    rffi.c_memset(mem.pointer, num.value, count.value)
    return null

c_ubytep = systemv.Pointer(systemv.types[u"ubyte"])

@builtin
@signature(Object)
def ref(mem):
    #mem = argument(argv, 0, Object)
    if isinstance(mem, Mem):
        size = simple.sizeof(mem.ctype)
        ctype = mem.ctype
    elif isinstance(mem, Uint8Array):
        size = rffi.sizeof(rffi.VOIDP)
        ctype = c_ubytep
    else:
        raise unwind(LTypeError(u"expected object that can be converted to c-object"))
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    result = systemv.AutoMem(systemv.Pointer(ctype), pointer, 1)
    result.setattr(u"to", mem)
    return result
