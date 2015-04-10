from simple import *
from space import Error, Object, List, String, null, signature, argument
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib import jit_libffi, clibffi, unroll

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
    u'longlong': Signed(rffi.sizeof(rffi.LONGLONG)),
    u'ulonglong': Unsigned(rffi.sizeof(rffi.ULONGLONG)),
    u'i8': Signed(1),
    u'i16': Signed(2),
    u'i32': Signed(4),
    u'i64': Signed(8),
    u'u8': Unsigned(1),
    u'u16': Unsigned(2),
    u'u32': Unsigned(4),
    u'u64': Unsigned(8),
}
#u'double': rffi.sizeof(rffi.DOUBLE),
#u'float': rffi.sizeof(rffi.FLOAT),
#u'longdouble': rffi.sizeof(rffi.LONGDOUBLE),

# Memory location in our own heap. Compare to 'handle'
# that is a record in a shared library.
class Mem(Object):
    def __init__(self, ctype, pointer):
        self.ctype = ctype
        self.pointer = pointer

    def getattr(self, name):
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            # or isinstance(tp, Array):
            if isinstance(ctype, Struct) or isinstance(ctype, Union):
                offset, ctype = ctype.namespace[name]
                pointer = rffi.ptradd(self.pointer, offset)
                if isinstance(ctype, Struct) or isinstance(ctype, Union):
                    return Mem(Pointer(ctype), pointer)
                elif isinstance(ctype, Signed) or isinstance(ctype, Unsigned) or isinstance(ctype, Pointer):
                    return ctype.load(pointer)
                else:
                    raise Error(u"no load supported for " + ctype.repr())
        raise Error(u"cannot attribute access other mem than structs or unions")

    def setattr(self, name, value):
        ctype = self.ctype
        if isinstance(ctype, Pointer):
            ctype = ctype.to
            if isinstance(ctype, Struct) or isinstance(ctype, Union):
                offset, ctype = ctype.namespace[name]
                pointer = rffi.ptradd(self.pointer, offset)
                if isinstance(ctype, Signed) or isinstance(ctype, Unsigned):
                    return ctype.store(pointer, value)
                else:
                    raise Exception(u"no store supported for " + ctype.repr())
        raise Error(u"cannot attribute access other mem than structs or unions")

    def call(self, argv):
        if isinstance(self.ctype, CFunc):
            return self.ctype.ccall(self.pointer, argv)
        raise Error(u"cannot call " + self.ctype.repr())

    def repr(self):
        name = self.ctype.repr()
        if self.ctype is null:
            name = u''
        return u"<%x %s>" % (rffi.cast(rffi.LONG, self.pointer), name)

class Pointer(Type):
    size = rffi.sizeof(rffi.VOIDP)
    def __init__(self, to):
        self.to = to
        self.align = self.size

    def cast_to_ffitype(self):
        return clibffi.ffi_type_pointer

    def load(self, offset):
        return Mem(self, rffi.cast(rffi.VOIDPP, offset)[0])

    def store(self, offset, value):
        if value is null:
            pointer = lltype.nullptr(rffi.VOIDP.TO)
        elif isinstance(value, Mem):
            # It could be worthwhile to typecheck the ctype here.
            pointer = value.pointer
        else:
            raise Error(u"cannot pointer store " + value.repr())
        ptr = rffi.cast(rffi.VOIDPP, offset)
        ptr[0] = pointer

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
            exchange_size = align(exchange_size, self.restype.align)
            exchange_size += sizeof(self.restype)
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
        # Exchange buffer is built for every call. Filled with arguments that are passed to the function.
        exc = lltype.malloc(rffi.VOIDP.TO, cif.exchange_size, flavor='raw')
        try:
            for i in range(argc):
                offset = rffi.ptradd(exc, cif.exchange_args[i])
                self.argtypes[i].store(offset, argv[i])
            jit_libffi.jit_ffi_call(cif, pointer, exc)
            val = null
            if isinstance(self.restype, Type):
                offset = rffi.ptradd(exc, cif.exchange_result)
                val = self.restype.load(offset)
        finally:
            lltype.free(exc, flavor='raw')
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
        raise Exception(u"cannot cfunc store " + value.repr())

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
        if isinstance(restype, Type):
            argtypes.append(argtype)
        else:
            raise Error(u"expected type as argtype, not " + argtype.repr())
    return CFunc(restype, argtypes)

class Struct(Type):
    def __init__(self, fields=None):
        self.align = 0
        self.fields = None
        self.namespace = {}
        self.offsets = []
        self.size = 0
        if fields is not None:
            self.declare(fields)

    def declare(self, fields):
        if self.fields is not None:
            raise Error(u"struct can be declared only once")
        self.fields = fields
        self.align = 1

        offset = 0
        for name, ctype in fields:
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
 
    def repr(self):
        if self.fields is None:
            return u'<opaque>'
        names = []
        for name, ctype in self.fields:
            names.append(u'.' + name)
        return u'<struct ' + u' '.join(names) + u'>'

@Struct.instantiator
@signature(Object)
def _(fields_list):
    if fields_list is null:
        return Struct(None)
    fields = []
    for field in fields_list.contents:
        name = field.getitem(Integer(0))
        ctype = field.getitem(Integer(1))
        if not (isinstance(name, String) and isinstance(ctype, Type)):
            raise Error(u"expected declaration format: [name, ctype]")
        fields.append((name.string, ctype))
    return Struct(fields)

class Union(Type):
    def __init__(self, fields):
        self.align = 0
        self.fields = None
        self.namespace = {}
        self.size = 0
        if fields is not None:
            self.declare(fields)

    def declare(self, fields):
        if self.fields is not None:
            raise Error(u"union can be declared only once")
        self.fields = fields
        self.align = 1

        offset = 0
        for name, ctype in fields:
            if ctype.parameter is not None:
                raise Error(u"parametric field in an union")
            self.align = max(self.align, ctype.align)
            self.size = max(self.size, sizeof(ctype))
            self.namespace[name] = (0, ctype)

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
        self.ctype = ctype
        if ctype.parameter is not None:
            raise Error(u"parametric field in an array")
        if length == 0:
            self.parameter = self
            self.size = 0
        else:
            self.size = sizeof(ctype) * int(length)
        self.align = ctype.align

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
