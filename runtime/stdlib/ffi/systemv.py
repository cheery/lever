from simple import *
from space import Error, Object, List, String, null, signature, argument, as_cstring, Uint8Array
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
    def __init__(self, ctype, pointer, length=0):
        self.ctype = ctype
        self.pointer = pointer
        self.length = length

    def getattr(self, name):
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            # or isinstance(tp, Array):
            if isinstance(ctype, Struct) or isinstance(ctype, Union):
                offset, ctype = ctype.namespace[name]
                pointer = rffi.ptradd(self.pointer, offset)
                if isinstance(ctype, Struct) or isinstance(ctype, Union) or isinstance(ctype, Array):
                    return Mem(Pointer(ctype), pointer)
                return ctype.load(pointer)
                #elif isinstance(ctype, Signed) or isinstance(ctype, Unsigned) or isinstance(ctype, Floating) or isinstance(ctype, Pointer):
                #    return ctype.load(pointer)
                #else:
                #    raise Error(u"no load supported for " + ctype.repr())
            elif isinstance(ctype, Type):
                if name == u"str" and ctype.size == 1:
                    s = rffi.charp2str(rffi.cast(rffi.CCHARP, self.pointer))
                    return String(s.decode('utf-8'))
                elif name == u"to":
                    return ctype.load(self.pointer)
        raise Error(u"cannot attribute access other mem than structs or unions")

    def setattr(self, name, value):
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            if isinstance(ctype, Struct) or isinstance(ctype, Union):
                offset, ctype = ctype.namespace[name]
                pointer = rffi.ptradd(self.pointer, offset)
                return ctype.store(pointer, value)
                #if isinstance(ctype, Signed) or isinstance(ctype, Unsigned) or isinstance(ctype, Floating) or isinstance(ctype, Pointer):
                #else:
                #    raise Exception(u"no store supported for " + ctype.repr())
            elif name == u"to":
                return ctype.store(self.pointer, value)
        raise Error(u"cannot attribute access other mem than structs or unions")

    def getitem(self, index):
        if not isinstance(index, Integer):
            raise Error(u"index must be an integer")
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
                return ctype.load(pointer)
        raise Error(u"cannot item access other mem than pointers or arrays")

    def setitem(self, index, value):
        if not isinstance(index, Integer):
            raise Error(u"index must be an integer")
        index = index.value
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            if isinstance(ctype, Array):
                pointer = rffi.ptradd(self.pointer, ctype.ctype.size*index)
                # TODO: could do length check if length present.
                return ctype.ctype.store(pointer, value)
            elif isinstance(ctype, Type):
                pointer = rffi.ptradd(self.pointer, ctype.size*index)
                return ctype.store(pointer, value)
        raise Error(u"cannot item access other mem than pointers or arrays")

    def call(self, argv):
        if isinstance(self.ctype, CFunc):
            return self.ctype.ccall(self.pointer, argv)
        raise Error(u"cannot call " + self.ctype.repr())

    def repr(self):
        name = self.ctype.repr()
        if self.ctype is null:
            name = u''
        return u"<%x %s>" % (rffi.cast(rffi.LONG, self.pointer), name)

# GC-allocated variation of the above.
class AutoMem(Mem):
    @rgc.must_be_light_finalizer
    def __del__(self):
        lltype.free(self.pointer, flavor='raw')

class Pointer(Type):
    size = rffi.sizeof(rffi.VOIDP)
    def __init__(self, to):
        self.to = to
        self.align = self.size

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset):
        pointer = rffi.cast(rffi.VOIDPP, offset)[0]
        if pointer == lltype.nullptr(rffi.VOIDP.TO):
            return null
        return Mem(self, pointer)

    def store(self, offset, value):
        if value is null:
            pointer = lltype.nullptr(rffi.VOIDP.TO)
        elif isinstance(value, Mem):
            # It could be worthwhile to typecheck the ctype here.
            if not self.typecheck(value.ctype):
                raise Error(u"incompatible pointer store: %s = %s" % (self.repr(), value.ctype.repr()))
            pointer = value.pointer
        elif isinstance(value, Uint8Array):
            pointer = rffi.cast(rffi.VOIDP, value.uint8data)
        else:
            raise Error(u"cannot pointer store %s to %s" % (value.repr(), self.repr()))
        ptr = rffi.cast(rffi.VOIDPP, offset)
        ptr[0] = pointer
        return value

    def store_string(self, offset, pointer):
        to = self.to
        if isinstance(to, Type) and to.size == 1:
            ptr = rffi.cast(rffi.VOIDPP, offset)
            ptr[0] = pointer
        else:
            raise Error(u"cannot pointer store string to %s" % self.repr())

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
        self.align = self.size
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
            assert isinstance(argtype, Type)
            exchange_size = align(exchange_size, max(8, argtype.align))
            cif.exchange_args[i] = exchange_size
            exchange_size += sizeof(argtype)
        #cif.exchange_result_libffi = exchange_size
        restype = self.restype
        if restype is null:
            exchange_size = align(exchange_size, 8)
            cif.exchange_result = exchange_size
            exchange_size += jit_libffi.SIZE_OF_FFI_ARG
        elif isinstance(restype, Type):
            exchange_size = align(exchange_size, max(8, restype.align))
            cif.exchange_result = exchange_size
            exchange_size += max(sizeof(restype), jit_libffi.SIZE_OF_FFI_ARG)
        else: # SIZE_OF_FFI_ARG
            assert False
        cif.exchange_size = align(exchange_size, 8)
        jit_libffi.jit_ffi_prep_cif(cif)
        self.cif = cif

    def ccall(self, pointer, argv):
        argc = len(argv)
        if argc != len(self.argtypes):
            raise Error(u"ffi call expects %d arguments" % argc)
        if self.notready:
            self.prepare_cif()
            self.notready = False
        cif = self.cif
        # String objects need to be converted and stored during the call.
        # I assume it's not a good idea to just generated some and expect them to
        # stick around.
        sbuf = []
        # Exchange buffer is built for every call. Filled with arguments that are passed to the function.
        exc = lltype.malloc(rffi.VOIDP.TO, cif.exchange_size, flavor='raw')
        try:
            for i in range(argc):
                offset = rffi.ptradd(exc, cif.exchange_args[i])
                arg = argv[i]
                arg_t = self.argtypes[i]
                if isinstance(arg, String) and isinstance(arg_t, Pointer):
                    arg = rffi.str2charp(as_cstring(arg))
                    sbuf.append(arg)
                    arg_t.store_string(offset, arg)
                else:
                    arg_t.store(offset, arg)
            jit_libffi.jit_ffi_call(cif, pointer, exc)
            val = null
            if isinstance(self.restype, Type):
                offset = rffi.ptradd(exc, cif.exchange_result)
                val = self.restype.load(offset)
        finally:
            lltype.free(exc, flavor='raw')
            for sb in sbuf:
                lltype.free(sb, flavor='raw')
        return val

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset):
        return Mem(self, rffi.cast(rffi.VOIDPP, offset)[0])

    def store(self, offset, value):
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
    if restype is not null and not isinstance(restype, Type):
        raise Error(u"expected type or null as restype, not " + restype.repr())
    argtypes = []
    for argtype in argtypes_list.contents:
        if isinstance(argtype, Type):
            argtypes.append(argtype)
        else:
            raise Error(u"expected type as argtype, not " + argtype.repr())
    return CFunc(restype, argtypes)

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
            raise Error(u"struct can be declared only once")
        self.fields = fields
        self.align = 1

        offset = 0
        for name, ctype in fields:
            assert isinstance(ctype, Type)
            if self.parameter is not None:
                raise Error(u"parametric field in middle of a structure")
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

    def load(self, offset):
        pointer = lltype.malloc(rffi.VOIDP.TO, self.size, flavor='raw')
        rffi.c_memcpy(pointer, offset, sizeof(self))
        return AutoMem(Pointer(self), pointer, 1)

    def store(self, offset, value):
        if isinstance(value, Mem):
            ctype = value.ctype
            if isinstance(ctype, Pointer) and ctype.to is self:
                rffi.c_memcpy(offset, value.pointer, sizeof(self))
                return value
        raise Error(u"cannot struct store " + value.repr())
 
    def repr(self):
        if self.fields is None:
            return u'<opaque %s>' % self.name
        names = []
        for name, ctype in self.fields:
            names.append(u'.' + name)
        return u'<struct ' + u' '.join(names) + u'>'

@Struct.instantiator
@signature(Object)
def _(fields_list):
    if fields_list is null:
        return Struct(None)
    if not isinstance(fields_list, List):
        raise Error(u"expected a list")
    fields = []
    for field in fields_list.contents:
        name = field.getitem(Integer(0))
        ctype = field.getitem(Integer(1))
        if not (isinstance(name, String) and isinstance(ctype, Type)):
            raise Error(u"expected declaration format: [name, ctype]")
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
            raise Error(u"union can be declared only once")
        self.fields = fields
        self.align = 1

        offset = 0
        for name, ctype in fields:
            assert isinstance(ctype, Type)
            if ctype.parameter is not None:
                raise Error(u"parametric field in an union")
            self.align = max(self.align, ctype.align)
            self.size = max(self.size, sizeof(ctype))
            self.namespace[name] = (0, ctype)

    def typecheck(self, other):
        if self is other:
            return True
        return False

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
        ctype = field.getitem(Integer(1))
        if not (isinstance(name, String) and isinstance(ctype, Type)):
            raise Error(u"expected declaration format: [name, ctype]")
        fields.append((name.string, ctype))
    return Union(fields)

class Array(Type):
    def __init__(self, ctype, length=0):
        assert isinstance(ctype, Type)
        self.ctype = ctype
        if ctype.parameter is not None:
            raise Error(u"parametric field in an array")
        if length == 0:
            self.parameter = self
            self.size = 0
        else:
            self.size = sizeof(ctype) * length
        self.align = ctype.align

    def cast_to_ffitype(self):
        return self.ctype.cast_to_ffitype()

    def typecheck(self, other):
        if isinstance(other, Pointer):
            return self.ctype.typecheck(other.to)
        if isinstance(other, Array):
            return self.ctype.typecheck(other.ctype)
        return False

    def load(self, offset):
        raise Error(u"array load notimpl")

    def store(self, offset, value):
        raise Error(u"Array store notimpl")

    def repr(self):
        return u'<array ' + self.ctype.repr() + u'>'

@Array.instantiator
def _(argv):
    ctype = argument(argv, 0, Type)
    if len(argv) >= 2:
        n = argument(argv, 1, Integer).value
    else:
        n = 0
    return Array(ctype, n)
