from simple import *
from space import *
#from space import OldError, unwind, LError, LTypeError, LCallError, Object, List, String, null, signature, as_cstring, Uint8Array
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit_libffi, clibffi, unroll, rgc

# Architecture dependent values. These must be right or
# otherwise we can't call foreign libraries.
types = {
    u'char': Unsigned(rffi.sizeof(rffi.CHAR)),
    u'byte': Unsigned(rffi.sizeof(rffi.CHAR)),
    u'sbyte': Signed(rffi.sizeof(rffi.SIGNEDCHAR)),
    u'ubyte': Unsigned(rffi.sizeof(rffi.UCHAR)),
    u'short': Signed(rffi.sizeof(rffi.SHORT)),
    u'ushort': Unsigned(rffi.sizeof(rffi.USHORT)),
    u'int': Signed(rffi.sizeof(rffi.INT)),
    u'uint': Unsigned(rffi.sizeof(rffi.UINT)),
    u'long': Signed(rffi.sizeof(rffi.LONG)),
    u'ulong': Unsigned(rffi.sizeof(rffi.ULONG)),
    u'llong': Signed(rffi.sizeof(rffi.LONGLONG)),
    u'ullong': Unsigned(rffi.sizeof(rffi.ULONGLONG)),
    u'size_t': Unsigned(rffi.sizeof(rffi.SIZE_T)),
    u'i8': Signed(1),
    u'i16': Signed(2),
    u'i32': Signed(4),
    u'i64': Signed(8),
    u'u8': Unsigned(1),
    u'u16': Unsigned(2),
    u'u32': Unsigned(4),
    u'u64': Unsigned(8),
    u'float': Floating(rffi.sizeof(rffi.FLOAT)),
    u'double': Floating(rffi.sizeof(rffi.DOUBLE)),
}
#u'longdouble': rffi.sizeof(rffi.LONGDOUBLE),

# Memory location in our own heap. Compare to 'handle'
# that is a record in a shared library.
class Mem(Object):
    def __init__(self, ctype, pointer, length=0, pool=None):
        self.ctype = ctype
        self.pointer = pointer
        self.length = length
        self.pool = pool

    def getattr(self, name):
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            if isinstance(ctype, Type):
                return ctype.on_getattr(self, name)
        return Object.getattr(self, name)

    def setattr(self, name, value):
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            if isinstance(ctype, Type):
                return ctype.on_setattr(self, name, value)
        return Object.setattr(self, name, value)

    def getitem(self, index):
        if not isinstance(index, Integer):
            return Object.getitem(self, index)
        # The getitem and setitem should be just like the getattr/setattr,
        # But we didn't do shadowed arrays or plain types yet. :)
        index = index.value
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            if isinstance(ctype, Array):
                ctype = ctype.ctype
                # TODO: could do length check if length present.
            if isinstance(ctype, Type):
                pointer = rffi.ptradd(self.pointer, ctype.size*index)
                if isinstance(ctype, Struct) or isinstance(ctype, Union) or isinstance(ctype, Array):
                    return Mem(Pointer(ctype), pointer)
                return ctype.load(pointer, False)
        return Object.getitem(self, Integer(index))

    def setitem(self, index, value):
        if not isinstance(index, Integer):
            return Object.setitem(self, index, value)
        index = index.value
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            if isinstance(ctype, Array):
                pointer = rffi.ptradd(self.pointer, ctype.ctype.size*index)
                # TODO: could do length check if length present.
                return ctype.ctype.store(self.pool, pointer, value)
            elif isinstance(ctype, Type):
                pointer = rffi.ptradd(self.pointer, ctype.size*index)
                return ctype.store(self.pool, pointer, value)
        return Object.setitem(self, Integer(index), value)

    def call(self, argv):
        if isinstance(self.ctype, CFunc):
            return self.ctype.ccall(self.pointer, argv)
        return Object.call(self, argv)

    def repr(self):
        name = self.ctype.repr()
        if self.ctype is null:
            name = u''
        return u"<%x %s>" % (rffi.cast(rffi.LONG, self.pointer), name)

    def iter(self):
        return MemIterator(self, self.length)

class MemIterator(Object):
    _immutable_fields_ = ['mem', 'length']
    def __init__(self, mem, length):
        self.mem = mem
        self.index = 0
        self.length = length

    def iter(self):
        return self

@MemIterator.method(u"next", signature(MemIterator))
def MemIterator_next(memi):
    if memi.index < memi.length:
        index = memi.index
        memi.index += 1
        return memi.mem.getitem(Integer(index))
    raise StopIteration()

def unroll_shadow(btype):
    ctype = btype
    while isinstance(ctype, Shadow):
        ctype = ctype.basetype
        if ctype is btype:
            raise unwind(LTypeError(u"Recursive type definition"))
    return ctype

# GC-allocated variation of the above.
class AutoMem(Mem):
    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self.pointer, flavor='raw')
        self.pointer = lltype.nullptr(rffi.VOIDP.TO)

class Pointer(Type):
    size = rffi.sizeof(rffi.VOIDP)
    def __init__(self, to):
        self.to = to
        self.align = self.size

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset, copy):
        pointer = rffi.cast(rffi.VOIDPP, offset)[0]
        if pointer == lltype.nullptr(rffi.VOIDP.TO):
            return null
        return Mem(self, pointer)

    def store(self, pool, offset, value):
        if value is null:
            ptr = rffi.cast(rffi.VOIDPP, offset)
            ptr[0] = lltype.nullptr(rffi.VOIDP.TO)
        elif isinstance(value, Mem):
            pool_mark_object(pool, value)
            # It could be worthwhile to typecheck the ctype here.
            if not self.typecheck(value.ctype):
                raise unwind(LTypeError(u"incompatible pointer store: %s = %s" % (self.repr(), value.ctype.repr())))
            ptr = rffi.cast(rffi.VOIDPP, offset)
            ptr[0] = value.pointer
        elif isinstance(value, Uint8Array):
            pool_mark_object(pool, value)
            ptr = rffi.cast(rffi.VOIDPP, offset)
            ptr[0] = rffi.cast(rffi.VOIDP, value.uint8data)
        elif pool is None:
            raise unwind(LTypeError(u"cannot store other than memory references into non-pool-backed pointers"))
        elif isinstance(value, String):
            to = self.to
            if isinstance(to, Type) and to.size == 1:
                pointer = rffi.str2charp(as_cstring(value))
                pointer = rffi.cast(rffi.VOIDP, pointer)
                ptr = rffi.cast(rffi.VOIDPP, offset)
                ptr[0] = pointer
                pool_mark(pool, pointer)
            else:
                raise unwind(LTypeError(u"cannot pointer store string to %s" % self.repr()))
        elif isinstance(value, List):
            # Won't possibly work in parametric objects.. hm.
            length = len(value.contents)
            if length > 0:
                pointer = pool_alloc(pool, sizeof_a(self.to, length))
                ptr = rffi.cast(rffi.VOIDPP, offset)
                ptr[0] = pointer
                mem = Mem(self, pointer, length, pool)
                for i, val in enumerate(value.contents):
                    mem.setitem(Integer(i), val)
            else:
                ptr = rffi.cast(rffi.VOIDPP, offset)
                ptr[0] = lltype.nullptr(rffi.VOIDP.TO)
        else:
            pointer = pool_alloc(pool, sizeof(self.to))
            ptr = rffi.cast(rffi.VOIDPP, offset)
            ptr[0] = pointer
            self.to.store(pool, pointer, value)
        #else:
        #    raise unwind(LTypeError(u"cannot pointer store %s to %s" % (value.repr(), self.repr())))
        return value

    def typecheck(self, other):
        if other is null:
            return True
        if isinstance(other, Pointer):
            if isinstance(self.to, Type):
                return self.to.typecheck(other.to)
            return True
        if isinstance(other, Array):
            if isinstance(self.to, Type):
                return self.to.typecheck(other.ctype)
            return True
        return False

    def repr(self):
        return u"<pointer %s>" % self.to.repr()

@Pointer.instantiator
@signature(Type)
def _(ctype):
    return Pointer(ctype)

class CFunc(Type):
    def __init__(self, restype, argtypes):
        self.align = rffi.sizeof(rffi.VOIDP)
        self.argtypes = argtypes
        self.cif = lltype.nullptr(jit_libffi.CIF_DESCRIPTION)
        self.notready = True
        self.restype = restype
        self.size = rffi.sizeof(rffi.VOIDP)

    def prepare_cif(self):
        argc = len(self.argtypes)

        # atypes points to an array of ffi_type pointers
        cif = lltype.malloc(jit_libffi.CIF_DESCRIPTION, argc, flavor='raw')
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
        exchange_size = align(exchange_size, 8)
        for i in range(argc):
            argtype = self.argtypes[i]
            assert isinstance(argtype, Type) # checked prior that this holds.
            exchange_size = align(exchange_size, max(8, argtype.align))
            cif.exchange_args[i] = int(exchange_size)
            exchange_size += sizeof(argtype)
        #cif.exchange_result_libffi = exchange_size
        restype = self.restype
        if restype is null:
            exchange_size = align(exchange_size, 8)
            cif.exchange_result = int(exchange_size)
            exchange_size += jit_libffi.SIZE_OF_FFI_ARG
        elif isinstance(restype, Type):
            exchange_size = align(exchange_size, max(8, restype.align))
            cif.exchange_result = int(exchange_size)
            exchange_size += max(sizeof(restype), jit_libffi.SIZE_OF_FFI_ARG)
        else: # SIZE_OF_FFI_ARG
            assert False # checked prior that this holds.
        cif.exchange_size = int(align(exchange_size, 8))
        jit_libffi.jit_ffi_prep_cif(cif)
        self.cif = cif

    def ccall(self, pointer, argv):
        argc = len(argv)
        if argc != len(self.argtypes):
            raise unwind(LCallError(len(self.argtypes), len(self.argtypes), False, argc))
        if self.notready:
            self.prepare_cif()
            self.notready = False
        cif = self.cif
        # String objects need to be converted and stored during the call.
        # Also, there are many things that are better treated like this.
        pool = Pool()
        #sbuf = []
        # Exchange buffer is built for every call. Filled with arguments that are passed to the function.
        exc = lltype.malloc(rffi.VOIDP.TO, cif.exchange_size, flavor='raw')
        try:
            for i in range(argc):
                offset = rffi.ptradd(exc, cif.exchange_args[i])
                arg = argv[i]
                arg_t = self.argtypes[i]
                # TODO: fixme
                arg_t.store(pool, offset, arg)
            jit_libffi.jit_ffi_call(cif, pointer, exc)
            val = null
            if isinstance(self.restype, Type):
                offset = rffi.ptradd(exc, cif.exchange_result)
                val = self.restype.load(offset, True)
        finally:
            lltype.free(exc, flavor='raw')
            pool.free_noreuse()
        return val

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset, copy):
        return Mem(self, rffi.cast(rffi.VOIDPP, offset)[0])

    def store(self, pool, offset, value):
        if isinstance(value, Mem):
            # It could be worthwhile to typecheck the ctype here.
            pnt = rffi.cast(rffi.VOIDPP, offset)
            pnt[0] = value.pointer
            return value
        raise Exception(u"cannot cfunc store " + value.repr())

    def typecheck(self, other):
        if self is other:
            return True
        return False

    def repr(self):
        string = u'<cfunc ' + self.restype.repr()
        for argtype in self.argtypes:
            string += u' ' + argtype.repr()
        return string + u'>'

@CFunc.instantiator
@signature(Object, List)
def _(restype, argtypes_list):
    argtypes = []
    for argtype in argtypes_list.contents:
        argtypes.append(to_type(argtype))
    return CFunc(to_type(restype), argtypes)

class Struct(Type):
    def __init__(self, fields=None, name=u''):
        self.align = 0
        self.fields = None
        self.namespace = {}
        self.offsets = []
        self.size = 0
        self.name = name
        if fields is not None:
            self.declare(fields)
	self.ffitype = lltype.nullptr(clibffi.FFI_STRUCT_P.TO)

    @rgc.must_be_light_finalizer
    def __del__(self):
        if self.ffitype:
            lltype.free(self.ffitype, flavor='raw')

    def cast_to_ffitype(self):
        if not self.ffitype:
            field_types = []
            for name, field in self.fields:
                field_types.append(field.cast_to_ffitype())
            self.ffitype = clibffi.make_struct_ffitype_e(self.size, self.align, field_types)
        return self.ffitype.ffistruct

    def declare(self, fields):
        if self.fields is not None:
            raise unwind(LError(u"struct can be declared only once"))
        self.fields = fields
        self.align = 1

        offset = 0
        for name, ctype in fields:
            if not isinstance(ctype, Type):
                raise unwind(LTypeError(u"expected ctype: " + ctype.repr()))
            if self.parameter is not None:
                raise unwind(LTypeError(u"parametric field in middle of a structure"))
            if ctype.parameter:
                self.parameter = ctype.parameter
            offset = align(offset, ctype.align)
            self.offsets.append(offset)
            self.align = max(self.align, ctype.align)
            self.namespace[name] = (offset, ctype)
            offset += sizeof(ctype)
        self.size = align(offset, self.align)

    def typecheck(self, other):
        if self is other:
            return True
        return False

    def on_getattr(self, mem, name):
        try:
            offset, ctype = self.namespace[name]
        except KeyError as ke:
            return Object.getattr(mem, name)
        pointer = rffi.ptradd(mem.pointer, offset)
        return ctype.load(pointer, False)

    def on_setattr(self, mem, name, value):
        try:
            offset, ctype = self.namespace[name]
        except KeyError as ke:
            return Object.setattr(mem, name, value)
        pointer = rffi.ptradd(mem.pointer, offset)
        return ctype.store(mem.pool, pointer, value)

    def load(self, offset, copy):
        if copy:
            pointer = lltype.malloc(rffi.VOIDP.TO, self.size, flavor='raw')
            rffi.c_memcpy(pointer, offset, sizeof(self))
            return AutoMem(Pointer(self), pointer, 1)
        else:
            return Mem(Pointer(self), offset, 1)

    def store(self, pool, offset, value):
        if isinstance(value, Mem):
            ctype = value.ctype
            if isinstance(ctype, Pointer) and ctype.to is self:
                rffi.c_memcpy(offset, value.pointer, sizeof(self))
                return value
        if isinstance(value, Dict):
            for key, obj in value.data.iteritems():
                if not isinstance(key, String):
                    raise unwind(LTypeError(u"dictionary fields must be string fields for struct.store to work"))
                try:
                    x, ctype = self.namespace[key.string]
                except KeyError as k:
                    raise unwind(LTypeError(u"%s not in %s" % (key.repr(), self.repr())))
                ctype.store(pool, rffi.ptradd(offset, x), obj)
            return value
        raise unwind(LTypeError(u"cannot struct store " + value.repr()))
 
    def repr(self):
        if self.fields is None:
            return u'<opaque %s>' % self.name
        names = []
        for name, ctype in self.fields:
            names.append(u'.' + name)
        return u'<struct ' + u' '.join(names) + u'>'

@Struct.instantiator
@signature(List)
def _(fields_list):
    fields = []
    for field in fields_list.contents:
        name = field.getitem(Integer(0))
        ctype = to_type(field.getitem(Integer(1)))
        if not isinstance(name, String):
            raise unwind(LTypeError(u"expected declaration format: [name, ctype]"))
        fields.append((name.string, ctype))
    return Struct(fields)

class Union(Type):
    def __init__(self, fields, name=u""):
        self.align = 0
        self.fields = None
        self.namespace = {}
        self.size = 0
        self.name = name
        if fields is not None:
            self.declare(fields)

    def declare(self, fields):
        if self.fields is not None:
            raise unwind(LError(u"union can be declared only once"))
        self.fields = fields
        self.align = 1

        offset = 0
        for name, ctype in fields:
            assert isinstance(ctype, Type)
            if ctype.parameter is not None:
                raise unwind(LTypeError(u"parametric field in an union"))
            self.align = max(self.align, ctype.align)
            self.size = max(self.size, sizeof(ctype))
            self.namespace[name] = (0, ctype)

    def typecheck(self, other):
        if self is other:
            return True
        return False

    def on_getattr(self, mem, name):
        try:
            offset, ctype = self.namespace[name]
        except KeyError as ke:
            return Object.getattr(mem, name)
        pointer = rffi.ptradd(mem.pointer, offset)
        return ctype.load(pointer, False)

    def on_setattr(self, mem, name, value):
        try:
            offset, ctype = self.namespace[name]
        except KeyError as ke:
            return Object.setattr(mem, name, value)
        pointer = rffi.ptradd(mem.pointer, offset)
        return ctype.store(mem.pool, pointer, value)

    def load(self, offset, copy):
        if copy:
            pointer = lltype.malloc(rffi.VOIDP.TO, self.size, flavor='raw')
            rffi.c_memcpy(pointer, offset, sizeof(self))
            return AutoMem(Pointer(self), pointer, 1)
        else:
            return Mem(Pointer(self), offset, 1)

    def store(self, pool, offset, value):
        if isinstance(value, Mem):
            ctype = value.ctype
            if isinstance(ctype, Pointer) and ctype.to is self:
                rffi.c_memcpy(offset, value.pointer, sizeof(self))
                return value
        if isinstance(value, Dict):
            for key, obj in value.data.iteritems():
                if not isinstance(key, String):
                    raise unwind(LTypeError(u"dictionary fields must be string fields for union.store to work"))
                try:
                    x, ctype = self.namespace[key.string]
                except KeyError as k:
                    raise unwind(LTypeError(u"%s not in %s" % (key.repr(), self.repr())))
                ctype.store(pool, rffi.ptradd(offset, x), obj)
            return value
        raise unwind(LTypeError(u"cannot union store " + value.repr()))

    def repr(self):
        names = []
        for name, ctype in self.fields:
            names.append(u'.' + name)
        return u'<union ' + u' '.join(names) + u'>'

@Union.instantiator
@signature(List)
def _(fields_list):
    if fields_list is null:
        return Union(None)
    fields = []
    for field in fields_list.contents:
        name = field.getitem(Integer(0))
        ctype = to_type(field.getitem(Integer(1)))
        if not isinstance(name, String):
            raise unwind(LTypeError(u"expected declaration format: [name, ctype]"))
        fields.append((name.string, ctype))
    return Union(fields)

class Array(Type):
    def __init__(self, ctype, length=0):
        assert isinstance(ctype, Type)
        self.ctype = ctype
        if ctype.parameter is not None:
            raise unwind(LTypeError(u"parametric field in an array"))
        if length == 0:
            self.parameter = self
            self.size = 0
        else:
            self.size = sizeof(ctype) * length
        self.align = ctype.align
        self.length = length

    def cast_to_ffitype(self):
        return self.ctype.cast_to_ffitype()

    def typecheck(self, other):
        if isinstance(other, Pointer):
            return self.ctype.typecheck(other.to)
        if isinstance(other, Array):
            return self.ctype.typecheck(other.ctype)
        return False

    def on_getattr(self, mem, name):
        if name == u"str" and self.ctype.size == 1:
            if self.length != 0:
                s = rffi.charp2strn(rffi.cast(rffi.CCHARP, mem.pointer), int(self.length))
            else:
                s = rffi.charp2str(rffi.cast(rffi.CCHARP, mem.pointer))
            return String(s.decode('utf-8'))
        raise Object.getattr(mem, name)

    def on_setattr(self, mem, name, value):
        raise Object.setattr(mem, name, value)

    def load(self, offset, copy):
        if copy:
            pointer = lltype.malloc(rffi.VOIDP.TO, self.size, flavor='raw')
            rffi.c_memcpy(pointer, offset, sizeof(self))
            return AutoMem(Pointer(self), pointer, 1)
        else:
            return Mem(Pointer(self), offset, 1)

    def store(self, pool, offset, value):
        if self.length == 0:
            raise OldError(u"Array length=0 store notimpl")
        elif isinstance(value, List):
            length = len(value.contents)
            if length != self.length:
                raise unwind(LTypeError(u"Array length [%d] = [%d] must match" % (self.length, length)))
            for i, val in enumerate(value.contents):
                self.ctype.store(pool, rffi.ptradd(offset, i*sizeof(self.ctype)), val)
            return value
        raise OldError(u"array store for %s notimpl" % value.repr())

    def repr(self):
        return u'<array ' + self.ctype.repr() + u'>'

@Array.instantiator
@signature(Object, Integer, optional=1)
def _(ctype, n):
    n = 0 if n is None else n.value
    return Array(to_type(ctype), n)

class PoolPointer:
    def __init__(self, pointer):
        self.pointer = pointer

    def free(self):
        lltype.free(self.pointer, flavor='raw')
        self.pointer = lltype.nullptr(rffi.VOIDP.TO)

class AutoPoolPointer(PoolPointer):
    @rgc.must_be_light_finalizer
    def __del__(self):
        if self.pointer != lltype.nullptr(rffi.VOIDP.TO):
            lltype.free(self.pointer, flavor='raw')
            self.pointer = lltype.nullptr(rffi.VOIDP.TO)

class Pool(Object):
    def __init__(self, autoclear=True, mode=PoolPointer):
        self.autoclear = autoclear
        self.mode = mode
        self.pointers = []
        self.refs = []

    def mark(self, pointer):
        self.pointers.append(self.mode(pointer))

    def mark_object(self, obj):
        self.refs.append(obj)
    
    def free_noreuse(self):
        for pointer in self.pointers:
            pointer.free()

    def free(self):
        for pointer in self.pointers:
            pointer.free()
        self.pointers = []
        self.refs = []

@Pool.instantiator2(signature(Boolean, optional=1))
def AutoPool_new(autoclear):
    return Pool((autoclear is None) or is_true(autoclear), AutoPoolPointer)

@Pool.method(u"alloc", signature(Pool, Type, Integer, Boolean, optional=2))
def Pool_alloc(pool, ctype, count, clear):
    if count:
        n = count.value
        size = sizeof_a(ctype, n)
    else:
        n = 1
        size = sizeof(ctype)
    pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
    pool.mark(pointer)
    if (pool.autoclear and clear is None) or is_true(clear):
        rffi.c_memset(pointer, 0, size)
    return Mem(Pointer(ctype), pointer, n, pool)

@Pool.method(u"mark", signature(Pool, Object))
def Pool_mark(pool, obj):
    pool.mark_object(obj)
    return null

@Pool.method(u"free", signature(Pool))
def Pool_free(pool):
    pool.free()
    return null

# Helpers that can be later associated to userspace -objects.
def pool_alloc(pool, size):
    if isinstance(pool, Pool):
        pointer = lltype.malloc(rffi.VOIDP.TO, size, flavor='raw')
        pool.mark(pointer)
        if pool.autoclear:
            rffi.c_memset(pointer, 0, size)
        return pointer
    elif pool is None:
        raise unwind(LError(u"Would have to allocate to do this action"))
    else:
        raise unwind(LError(u"pool alloc with user objects not implemented"))

def pool_mark(pool, pointer):
    if isinstance(pool, Pool):
        pool.mark(pointer)
    elif pool is None:
        assert False, "usually at this point, your porridge is burned already"
    else:
        raise unwind(LError(u"pool mark with user objects not implemented"))

def pool_mark_object(pool, obj):
    if isinstance(pool, Pool):
        pool.mark_object(obj)
    elif pool is not None: # We just don't mark user objects if no pool present.
        raise unwind(LError(u"pool mark with user objects not implemented"))
