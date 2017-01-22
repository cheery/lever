from rpython.rlib import rdynload, objectmodel, clibffi, rgc, rgil
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from simple import Type, to_type
from space import *
from systemv import Mem, Pointer, CFunc, Struct, Union, Array
from bitmask import Bitmask
import core
import simple
import space
import systemv
import sys, os

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

class Handle(Mem):
    def __init__(self, library, name, pointer, ctype):
        Mem.__init__(self, ctype, pointer)
        self.library = library
        self.name = name
        #self.pointer = pointer
        #self.ctype = ctype

# Not needed with Mem handle.
#    def call(self, argv):
#        if isinstance(self.ctype, CFunc):
#            return self.ctype.ccall(self.pointer, argv)
#        return Object.call(self, argv)

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
    if isinstance(obj, Uint8Data):
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

@builtin
@signature(Mem, Object, Integer)
def memcpy(dst, src, count):
    if isinstance(src, Mem):
        src_pointer = src.pointer
    elif isinstance(src, Uint8Data):
        src_pointer = rffi.cast(rffi.VOIDP, src.uint8data)
    else:
        raise unwind(LTypeError(u"expected mem or array"))
    rffi.c_memcpy(dst.pointer, src_pointer, count.value)
    return dst

c_ubytep = systemv.Pointer(systemv.types[u"ubyte"])

@builtin
@signature(Object)
def ref(mem):
    #mem = argument(argv, 0, Object)
    if isinstance(mem, Mem):
        size = simple.sizeof(mem.ctype)
        ctype = mem.ctype
    elif isinstance(mem, Uint8Data):
        size = rffi.sizeof(rffi.VOIDP)
        ctype = c_ubytep
    else:
        raise unwind(LTypeError(u"expected object that can be converted to c-object"))
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    result = systemv.AutoMem(systemv.Pointer(ctype), pointer, 1)
    result.setattr(u"to", mem)
    return result

# Function callbacks
class Callback(Mem):
    def __init__(self, cfunc, callback):
        self.cfunc = cfunc
        self.callback = callback
        pointer = rffi.cast(rffi.VOIDP, clibffi.closureHeap.alloc())
        if cfunc.notready:
            cfunc.prepare_cif()
            cfunc.notready = False
        Mem.__init__(self, cfunc, pointer)

        closure_ptr = rffi.cast(clibffi.FFI_CLOSUREP, self.pointer)
        # hide the object
        gcref = rgc.cast_instance_to_gcref(self)
        raw = rgc.hide_nonmovable_gcref(gcref)
        unique_id = rffi.cast(rffi.VOIDP, raw)

        res = clibffi.c_ffi_prep_closure(closure_ptr, cfunc.cif.cif,
            invoke_callback, unique_id)

        if rffi.cast(lltype.Signed, res) != clibffi.FFI_OK:
            raise unwind(LError(u"libffi failed to build this callback"))
        if closure_ptr.c_user_data != unique_id:
            raise unwind(LError(u"ffi_prep_closure(): bad user_data"))

        # The function might be called in separate thread,
        # so allocate GIL here, just in case.
        rgil.allocate()

    def __del__(self): # Move into  separate class if this not sufficient.
        clibffi.closureHeap.free(rffi.cast(clibffi.FFI_CLOSUREP, self.pointer))

@Callback.instantiator
@signature(Type, Object)
def _(cfunc, callback):
    if isinstance(cfunc, Pointer):
        cfunc = cfunc.to
    cfunc = space.cast(cfunc, CFunc, u"callback")
    return Callback(cfunc, callback)

module.setattr_force(u"callback", Callback.interface)

def invoke_callback(ffi_cif, ll_res, ll_args, ll_userdata):
    """ Callback specification.
    ffi_cif - something ffi specific, don't care
    ll_args - rffi.VOIDPP - pointer to array of pointers to args
    ll_res - rffi.VOIDP - pointer to result
    ll_userdata - a special structure which holds necessary information
                  (what the real callback is for example), casted to VOIDP
    """
    # Reveal the callback.
    addr = rffi.cast(llmemory.Address, ll_userdata)
    gcref = rgc.reveal_gcref(addr)
    callback = rgc.try_cast_gcref_to_instance(Callback, gcref)
    if callback is None:
        try:
            os.write(STDERR,
                "Critical error: invoking a callback that was already freed\n")
        except:
            pass
        # We cannot do anything here.
    else:
        #must_leave = False
        try:
            # must_leave = space.threadlocals.try_enter_thread(space)
            # Should check for separate threads here and crash
            # if the callback comes from a thread that has no execution context.
            cfunc = callback.cfunc
            argv = []
            for i in range(0, len(cfunc.argtypes)):
                argv.append( cfunc.argtypes[i].load(ll_args[i], False) )
            value = callback.callback.call(argv)
            if isinstance(cfunc.restype, Type):
                cfunc.restype.store(None, ll_res, value)
        except Unwinder as unwinder:
            core.root_unwind(core.get_ec(), unwinder)
        except Exception as e:
            try:
                os.write(STDERR, "SystemError: callback raised ")
                os.write(STDERR, str(e))
                os.write(STDERR, "\n")
            except:
                pass
#        if must_leave:
#            space.threadlocals.leave_thread(space)

STDERR = 2
# 
# def invoke_callback(ffi_cif, ll_res, ll_args, ll_userdata):
#     cerrno._errno_after(rffi.RFFI_ERR_ALL | rffi.RFFI_ALT_ERRNO)
#     ll_res = rffi.cast(rffi.CCHARP, ll_res)
#     callback = reveal_callback(ll_userdata)
#     if callback is None:
#         # oups!
#         try:
#             os.write(STDERR, "SystemError: invoking a callback "
#                              "that was already freed\n")
#         except:
#             pass
#         # In this case, we don't even know how big ll_res is.  Let's assume
#         # it is just a 'ffi_arg', and store 0 there.
#         misc._raw_memclear(ll_res, SIZE_OF_FFI_ARG)
#     else:
#         callback.invoke(ll_res, rffi.cast(rffi.CCHARP, ll_args))
#     cerrno._errno_before(rffi.RFFI_ERR_ALL | rffi.RFFI_ALT_ERRNO)
