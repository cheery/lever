from inspect import getargs, getsourcefile, getsourcelines
from rpython.rlib import unroll
from rpython.rlib.objectmodel import (
    always_inline,
    compute_hash,
    not_rpython,
    specialize,
    r_dict,
)
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rbigint import rbigint

# Objects are a large tagged union. RPython requires
# that this common superclass is provided for all objects
# user can access from within the runtime.
class Object:
    static_kind = None

    @property
    def kind(self):
        return self.static_kind

# Resolving methods on interfaces help to ensure that
# interface block corresponds with the type of an object.
class Kind(Object):
    static_kind = None
    def __init__(self):
        self.properties = r_dict(eq_fn, hash_fn, force_non_null=True)

# Because the property list is an ordinary dictionary entry, it means
# that we must short-circuit the eq and hash lookup for some elements. 
def eq_fn(a, b):
    if isinstance(a, Atom) and isinstance(b, Atom):
        return (a is b)
    elif isinstance(a, Compound) and isinstance(b, Compound):
        if not (a.atom is b.atom):
            return False
        if len(a.items) != len(b.items):
            return False
        for i in range(len(a.items)):
            if not eq_fn(a.items[i], b.items[i]):
                return False
        return True
    elif isinstance(a, Operator) and isinstance(b, Operator):
        return (a is b)
    elif isinstance(a, Kind) and isinstance(b, Kind):
        return (a is b)
    elif isinstance(a, String) and isinstance(b, String):
        return (a.string == b.string)
    if convert(call(op_eq, [a, b], 1), BoolKind) is true:
        return True
    else:
        return False

def hash_fn(a):
    if isinstance(a, Atom):
        return compute_hash(a)
    elif isinstance(a, Compound):
        mult = 1000003
        x = 0x345678
        z = len(a.items)
        for item in a.items:
            y = hash_fn(item)
            x = (x ^ y) * mult
            z -= 1
            mult += 82520 + z + z
        x += 97531
        return intmask(x)
    elif isinstance(a, Operator):
        return compute_hash(a)
    elif isinstance(a, Kind):
        return compute_hash(a)
    elif isinstance(a, String):
        return compute_hash(a.string)
    x = unwrap_int(cast(call(op_hash, [a], 1), Integer))
    return intmask(x)

# KindSheetKind -name is there to illustrate that
# the kind is a representational object we use to
# keep a record of things in order to implement them.
Kind.static_kind = KindSheetKind = Kind()

class Constant(Object):
    static_kind = None
    def __init__(self, dynamic_kind):
        self.dynamic_kind = dynamic_kind
        self.properties = r_dict(eq_fn, hash_fn, force_non_null=True)

    @property
    def kind(self):
        return self.dynamic_kind

BoolKind = Kind()
true = Constant(BoolKind)
false = Constant(BoolKind)

# Atoms and compounds are necessary in describing the kind sheets.
AtomKind = Kind()
class Atom(Object):
    static_kind = AtomKind
    def __init__(self, arity):
        self.arity = arity
        self.properties = r_dict(eq_fn, hash_fn, force_non_null=True)

CompoundKind = Kind()
class Compound(Object):
    static_kind = CompoundKind
    def __init__(self, atom, items):
        self.atom = atom
        self.items = items
        if atom.arity == 0:
            raise error(e_BugEmptyCompound)
        if atom.arity != len(items):
            raise error(e_CompoundArityError,
                wrap(atom.arity), wrap(len(items)))

IntegerKind = Kind()
class Integer(Object):
    static_kind = IntegerKind
    def __init__(self, bignum):
        self.bignum = bignum

StringKind = Kind()
class String(Object):
    static_kind = StringKind
    def __init__(self, string):
        self.string = string

TupleKind = Kind()
class Tuple(Object):
    static_kind = TupleKind
    def __init__(self, items):
        self.items = items

ListKind = Kind()
class List(Object):
    static_kind = ListKind
    def __init__(self, contents):
        self.contents = contents

DictKind = Kind()
class Dict(Object):
    static_kind = DictKind
    def __init__(self, contents):
        self.contents = contents

def new_dict():
    return Dict(r_dict(eq_fn, hash_fn, force_non_null=True))

SetKind = Kind()
class Set(Object):
    static_kind = SetKind
    def __init__(self, contents):
        self.contents = contents

def new_set():
    return Set(r_dict(eq_fn, hash_fn, force_non_null=True))

ImmutableListKind = Kind()
class ImmutableList(Object):
    static_kind = ImmutableListKind
    def __init__(self, contents):
        self.contents = contents

ImmutableDictKind = Kind()
class ImmutableDict(Object):
    static_kind = ImmutableDictKind
    def __init__(self, contents):
        self.contents = contents

def new_immutable_dict():
    return ImmutableSet(r_dict(eq_fn, hash_fn, force_non_null=True))

ImmutableSetKind = Kind()
class ImmutableSet(Object):
    static_kind = ImmutableSetKind
    def __init__(self, contents):
        self.contents = contents

def new_immutable_set():
    return ImmutableSet(r_dict(eq_fn, hash_fn, force_non_null=True))

IteratorKind = Kind()
class Iterator(Object):
    static_kind = IteratorKind
    def next(self):
        raise StopIteration()

@specialize.argtype(0)
def wrap(a):
    if isinstance(a, bool):
        return true if a else false
    if isinstance(a, int):
        return Integer(rbigint.fromint(a))
    if isinstance(a, str):
        return String(a.decode('utf-8'))
    if isinstance(a, unicode):
        return String(a)
    assert False, ""

def unwrap_int(a): # TODO: Should this thing have a better error?
    try:
        return a.bignum.toint()
    except OverflowError:
        raise error(e_OverflowError)

BuiltinKind = Kind()
class Builtin(Object):
    static_kind = BuiltinKind
    def __init__(self, function, argc, optc, outc, prefill=[]):
        self.function = function
        self.argc = argc
        self.optc = optc
        self.outc = outc
        self.prefill = prefill
        self.properties = r_dict(eq_fn, hash_fn, force_non_null=True)

BuiltinPortalKind = Kind()
class BuiltinPortal(Object):
    static_kind = BuiltinPortalKind
    def __init__(self, function):
        self.function = function

def prefill(builtin, prefill):
    return Builtin(builtin.function,
        argc = builtin.argc-1,
        optc = min(builtin.argc-1, builtin.optc),
        outc = builtin.outc,
        prefill = builtin.prefill + prefill)

def builtin(outc):
    def _decorator_(function):
        return python_bridge(function, outc)
    return _decorator_

@not_rpython
def python_bridge(function, outc):
    args, varargs, keywords = getargs(function.__code__)
    defaults = function.__defaults__ or ()
    argc = max(len(args), 0)
    optc = max(len(defaults), 0)
    argi = unroll.unrolling_iterable(range(argc-optc))
    argj = unroll.unrolling_iterable(range(argc-optc, argc))
    sourcefile       = getsourcefile(function)
    name             = function.__name__
    lines, lno0 = getsourcelines(function)
    lno1 = lno0 + len(lines)
    def py_bridge(argv):
        args = ()
        length = len(argv)
        if length < argc - optc:
            raise error(e_ArgumentCountError,
                wrap(argc), wrap(optc), wrap(length))
        if argc < length:
            raise error(e_ArgumentCountError,
                wrap(argc), wrap(optc), wrap(length))
        for i in argi:
            args += (argv[i],)
        for i in argj:
            if i < length:
                args += (argv[i],)
            else:
                args += (defaults[i+optc-argc],)
        try:
            result = function(*args)
        except OperationError as oe:
            oe.trace.append(BuiltinTraceEntry(sourcefile, lno0, lno1, name))
            raise
        if result is None:
            ret = []
        #elif isinstance(result, Tuple):
        #    ret = result.items
        else:
            ret = [result]
        if len(ret) != outc:
            raise error(e_BugResultCountError, wrap(outc), wrap(len(ret)))
        return ret
    py_bridge.__name__ = function.__name__
    return Builtin(py_bridge, argc, optc, outc)

def error(atom, *args):
    return OperationError(ErrorCompound(atom, list(args)))

class OperationError(Exception):
    def __init__(self, error):
        if isinstance(error, ErrorCompound):
            self.error = error
            self.trace = self.error.trace
        elif isinstance(error, Compound):
            self.error = ErrorCompound(error.atom, error.items)
            self.trace = self.error.trace
        elif isinstance(error, Atom):
            self.error = ErrorCompound(error, [])
            self.trace = self.error.trace
        else:
            self.error = error
            self.trace = []

BuiltinTraceEntryKind = Kind()
class BuiltinTraceEntry(Object):
    static_kind = BuiltinTraceEntryKind
    def __init__(self, sourcefile, lno0, lno1, name):
        self.sourcefile = sourcefile
        self.lno0 = lno0
        self.lno1 = lno1
        self.name = name
    
ErrorCompoundKind = Kind()
class ErrorCompound(Object):
    static_kind = ErrorCompoundKind
    def __init__(self, atom, items, trace=None):
        self.atom = atom
        self.items = items
        self.trace = [] if trace is None else trace
        if atom.arity != len(items):
            raise error(e_ErrorCompoundArityError,
                wrap(atom.arity), wrap(len(items)))

# Category for conditions that failed in builtin functions.
e_BugError = Atom(0)
e_BugResultCountError = Atom(2)
e_BuggedConversion = Atom(2)
e_BugAbstractMethod = Atom(0)
e_BugEmptyCompound = Atom(0)

# Every error that is supposed to be discoverable statically
# iff the type inference succeeds is in the TypeError category.  
e_TypeError = Atom(0)
e_ArgumentCountError = Atom(3)
e_ResultCountError = Atom(2)
e_CompoundArityError      = Atom(2)
e_ErrorCompoundArityError = Atom(2)
e_NoCoercion = Atom(2)
e_NoMethod   = Atom(2)
e_NoConversion = Atom(2)
e_NoAttr = Atom(1)
e_SelectorExceedsArgumentCount = Atom(0)
e_AlreadySet = Atom(1)
e_ModuleAlreadyLoaded = Atom(1)

# These errors do not have a category yet.
e_IOError           = Atom(0)
e_JSONDecodeError   = Atom(1)
e_IntegerParseError = Atom(0)
e_OverflowError = Atom(0)
e_ModuleError = Atom(0)
e_EvalError = Atom(0)
e_IntegerBaseError = Atom(0)
e_PreconditionFailed  = Atom(0) # Previous 'PartialOnArgument'
e_AssertFailed        = Atom(0)

# The post condition failed category.
e_PostconditionFailed = Atom(0)
e_NoItems = Atom(0)
e_NoIndex = Atom(0)
e_NoValue = Atom(0)

OperatorKind = Kind()
class Operator(Object):
    static_kind = OperatorKind
    def __init__(self, selectors, argc, default=None):
        self.argc = argc # the minimum number of arguments required.
        self.selectors = selectors
        self.default = default
        self.properties = r_dict(eq_fn, hash_fn, force_non_null=True)
        for selector in self.selectors:
            if selector >= argc:
                raise error(e_SelectorExceedsArgumentCount)

# call takes the callee and a tuple as arguments.
op_call = Operator([0], 2)

@builtin(1)
def op_eq_default(a, b):
    return wrap(a is b)
op_eq   = Operator([0, 1], 2, op_eq_default)

# hash function takes in a function to hash.
op_hash = Operator([0], 2)
# invariate
op_invariate = Operator([0], 2)

op_in = Operator([1], 2)
op_getitem = Operator([0], 2)
op_setitem = Operator([0], 3)
# op_iter is a conversion to IteratorKind now.
# tuple extraction is a conversion to TupleKind now.
# TODO: There is also the indexers that need to be implemented.

op_getslot = Operator([0], 1)
op_setslot = Operator([0], 2)
 
# match returns 'true' if the given object matches on the pattern.
op_match = Operator([0], 2)
op_unpack = Operator([0], 2)

# The prelude will provide an advanced stringifier.
# Therefore we don't have op_form here.

op_shl = Operator([0], 2) # left shift
op_shr = Operator([0], 2) # right shift

# all comparison operations are derived from the op_cmp
op_cmp = Operator([0,1], 2)
 
op_concat = Operator([0,1], 2)
op_copy = Operator([0], 1)

op_neg = Operator([0], 1)
op_pos = Operator([0], 1)
 
op_add = Operator([0,1], 2)
op_sub = Operator([0,1], 2)
op_mul = Operator([0,1], 2)
 
op_div = Operator([0,1], 2)
op_mod = Operator([0,1], 2)
op_floordiv = Operator([0,1], 2) # floordiv(a, b)
op_divrem = Operator([0,1], 2)
 
op_not = Operator([0], 1)   # ~
op_and = Operator([0,1], 2) # &
op_or  = Operator([0,1], 2) # |
op_xor = Operator([0,1], 2) # xor(a,b)
 
op_clamp = Operator([0], 3) # clamp(a, min,max)
op_abs = Operator([0], 1)
op_length = Operator([0], 1)
op_normalize = Operator([0], 1)
op_distance = Operator([0,1], 2)
op_dot = Operator([0,1], 2)
op_reflect = Operator([0,1], 2)
op_refract = Operator([0,1], 3) # refract(a,b,eta)
op_pow = Operator([0,1], 2)
 
# Stringify is different to many operators in that it returns
# NoValue by default on objects that do not have it. It is meant
# for stringifying short and flat objects.
@builtin(1)
def op_stringify_default(_):
    raise OperationError(ErrorCompound(e_NoValue, []))
op_stringify = Operator([0], 1, op_stringify_default)

# When users define new operators, they may need to
# provide some methods for existing types. Therefore
# each operator have their own property list.

# Every operator is resolved by selectors, in the same
# manner. If the kind sheet doesn't provide an
# implementation, it will attempt to obtain implementation
# from the operator.
def operator_call(op, args):
    op = cast(op, Operator)
    L = len(op.selectors)
    # operator argc is a characteristic argument count. There
    # must be at least that many arguments. If the user supplies more
    # then the implementation must accept more arguments.
    if len(args) < op.argc:
        raise OperationError(ErrorCompound(e_ArgumentCountError,
            [wrap(op.argc), wrap(0), wrap(len(args))]))
    if L == 1:
        index = op.selectors[0]
        kind = args[index].kind
        needs_coerce = False
    else:
        kinds = {}
        for index in op.selectors:
            kinds[args[index].kind] = None
        kind = unique_coercion(kinds)
        if kind is None:
            if op.default is not None:
                return callv(op.default, args)
            raise OperationError(ErrorCompound(e_NoCoercion, [op,
                ImmutableList(list(kinds))]))
        needs_coerce = True
    impl = kind.properties.get(op, None)
    if impl is None:
        impl = op.properties.get(kind, None)
    if impl is None:
        if op.default is not None:
            return callv(op.default, args)
        raise OperationError(ErrorCompound(e_NoMethod, [op, kind]))
    if needs_coerce:
        args = list(args)
        for index in op.selectors:
            args[index] = coerce(args[index], kind)
    return callv(impl, args)
OperatorKind.properties[op_call] = BuiltinPortal(operator_call)

# The operator handling needs coercion
def unique_coercion(kinds):
    s = []
    for y in kinds:
        ok = True
        for x in kinds:
            ok = ok and (x == y or has_coercion(x, y))
        if ok:
            s.append(y)
    if len(s) == 1:
        return s[0]
    return None

# These first atoms provide tools to implement coercion/conversion.
atom_coercion   = Atom(2)
atom_conversion = Atom(2)

def has_coercion(x, y):
    c = Compound(atom_coercion, [x, y])
    conv = y.properties.get(c, None)
    if conv is None:
        conv = x.properties.get(c, None)
    return (conv is not None)

def coerce(x, kind):
    xkind = x.kind
    if xkind is kind:
        return x
    else:
        c = Compound(atom_coercion, [xkind, kind])
        conv = kind.properties.get(c, None)
        if conv is None:
            conv = xkind.properties.get(c, None)
        if conv is None:
            raise OperationError(ErrorCompound(e_NoConversion,
                [x, kind]))
        return call(conv, [x], 1)
 
def convert(x, kind):
    xkind = x.kind
    if xkind is kind:
        return x
    else:
        c = Compound(atom_conversion, [xkind, kind])
        conv = kind.properties.get(c, None)
        if conv is None:
            conv = xkind.properties.get(c, None)
        if conv is None:
            d = Compound(atom_coercion, [xkind, kind])
            conv = kind.properties.get(d, None)
            if conv is None:
                conv = xkind.properties.get(d, None)
        if conv is None:
            raise OperationError(ErrorCompound(e_NoConversion,
                [x, kind]))
        return call(conv, [x], 1)

@specialize.arg(1)
def cast(obj, cls):
    if isinstance(cls, Kind):
        kind = cls
        return convert(obj, kind)
    else:
        assert cls.static_kind is not None
        kind = cls.static_kind
        obj = convert(obj, kind)
        if isinstance(obj, cls):
            return obj
    raise OperationError(ErrorCompound(e_BuggedConversion,
        [obj, cls.static_kind]))

# Every call made by the runtime must resolve to a builtin.
@specialize.arg(2)
def call(callee, args, outc=1):
    result = callv(callee, args)
    if len(result) != outc:
        raise OperationError(ErrorCompound(e_ResultCountError,
            [wrap(outc), wrap(len(result))]))
    if outc == 1:
        return result[0]
    else:
        res = ()
        for i in range(outc):
            res += (result[i],)
        return res
 
def callv(callee, args):
    while not isinstance(callee, Builtin):
        kind = callee.kind
        impl = kind.properties.get(op_call, None)
        if impl is None:
            raise OperationError(ErrorCompound(e_NoMethod, [op_call, kind]))
        if isinstance(impl, BuiltinPortal):
            return impl.function(callee, args)
        args.insert(0, callee)
        callee = impl
    return callee.function(callee.prefill + args)


atom_getattr = Atom(1)
atom_setattr = Atom(1)
atom_dynamic_getattr = Atom(0)
atom_dynamic_setattr = Atom(0)

def get_attribute(obj, name):
    kind = obj.kind
    attr = Compound(atom_getattr, [name])
    impl = kind.properties.get(attr, None)
    if impl is None:
        impl = kind.properties.get(atom_dynamic_getattr, None)
        if impl is None:
            raise OperationError(ErrorCompound(e_NoAttr,
                [name]))
        impl = call(impl, [name])
    return call(impl, [obj])

def set_attribute(obj, name, value):
    kind = obj.kind
    attr = Compound(atom_setattr, [name])
    impl = kind.properties.get(attr, None)
    if impl is None:
        impl = kind.properties.get(atom_dynamic_setattr, None)
        if impl is None:
            raise OperationError(ErrorCompound(e_NoAttr, [name]))
        impl = call(impl, [name])
    call(impl, [obj, value], 0)

# Helper decorators for describing the runtime.
@not_rpython
def method(kind_cls, operator, outc):
    if isinstance(kind_cls, Kind):
        kind = kind_cls
    else:
        assert kind_cls.static_kind is not None
        kind = kind_cls.static_kind
    def _decorator_(function):
        kind.properties[operator] = python_bridge(function, outc)
        return function
    return _decorator_

@not_rpython
def getter(kind_cls, name, outc):
    if isinstance(kind_cls, Kind):
        kind = kind_cls
    else:
        assert kind_cls.static_kind is not None
        kind = kind_cls.static_kind
    attr = Compound(atom_getattr, [wrap(name)])
    def _decorator_(function):
        kind.properties[attr] = python_bridge(function, outc)
        return function
    return _decorator_

@not_rpython
def setter(kind_cls, name):
    if isinstance(kind_cls, Kind):
        kind = kind_cls
    else:
        assert kind_cls.static_kind is not None
        kind = kind_cls.static_kind
    attr = Compound(atom_setattr, [wrap(name)])
    def _decorator_(function):
        kind.properties[attr] = python_bridge(function, 0)
        return function
    return _decorator_

@not_rpython
def attr_method(face, name, outc):
    if isinstance(cls, Kind):
        kind = cls
    else:
        assert cls.static_kind is not None
        kind = cls.static_kind
    attr = Compound(atom_getattr, [wrap(name)])
    def _decorator_(function):
        w_fn = python_bridge(function)
        def _wrapper_(a):
            return prefill(w_fn, [a])
        kind.properties[attr] = python_bridge(_wrapper_, 1)
        return function
    return _decorator_

variables = {
    u"KindSheetKind": KindSheetKind,
    u"BoolKind": BoolKind,
    u"true": true,
    u"false": false,
    u"AtomKind": AtomKind,
    u"CompoundKind": CompoundKind,
    u"IntegerKind": IntegerKind,
    u"StringKind": StringKind,
    u"TupleKind": TupleKind,
    u"ListKind": ListKind,
    u"DictKind": DictKind,
    u"SetKind": SetKind,
    u"ImmutableListKind": ImmutableListKind,
    u"ImmutableDictKind": ImmutableDictKind,
    u"ImmutableSetKind": ImmutableSetKind,
    u"IteratorKind": IteratorKind,
    u"BuiltinKind": BuiltinKind,
    u"BuiltinTraceEntryKind": BuiltinTraceEntryKind,
    u"ErrorCompoundKind": ErrorCompoundKind,
    u"BugError": e_BugError,
    u"BugResultCountError": e_BugResultCountError,
    u"BuggedConversion": e_BuggedConversion,
    u"TypeError": e_TypeError,
    u"ArgumentCountError": e_ArgumentCountError,
    u"ResultCountError": e_ResultCountError,
    u"CompoundArityError": e_CompoundArityError,
    u"ErrorCompoundArityError": e_ErrorCompoundArityError,
    u"NoCoercion": e_NoCoercion,
    u"NoMethod": e_NoMethod,
    u"NoConversion": e_NoConversion,
    u"NoAttr": e_NoAttr,
    u"SelectorExceedsArgumentCount": e_SelectorExceedsArgumentCount,
    u"IOError": e_IOError,
    u"JSONDecodeError": e_JSONDecodeError,
    u"IntegerParseError": e_IntegerParseError,
    u"OverflowError": e_OverflowError,
    u"ModuleError": e_ModuleError,
    u"EvalError": e_EvalError,
    u"IntegerBaseError": e_IntegerBaseError,
    u"PreconditionFailed": e_PreconditionFailed,
    u"AssertFailed": e_AssertFailed,
    u"PostconditionFailed": e_PostconditionFailed,
    u"NoItems": e_NoItems,
    u"NoIndex": e_NoIndex,
    u"NoValue": e_NoValue,
    u"OperatorKind": OperatorKind,
    u"call": op_call,
    u"==": op_eq,
    u"hash": op_hash,
    u"invariate": op_invariate,
    u"in": op_in,
    u"getitem": op_getitem,
    u"setitem": op_setitem,
    u"getslot": op_getslot,
    u"setslot": op_setslot,
    u"match": op_match,
    u"unpack": op_unpack,
    u"<<": op_shl,
    u">>": op_shr,
    u"cmp": op_cmp,
    u"++": op_concat,
    u"copy": op_copy,
    u"-expr": op_neg,
    u"+expr": op_pos,
    u"+": op_add,
    u"-": op_sub,
    u"*": op_mul,
    u"/": op_div,
    u"%": op_mod,
    u"//": op_floordiv,
    u"divrem": op_divrem,
    u"~": op_not,
    u"&": op_and,
    u"|": op_or,
    u"xor": op_xor,
    u"clamp": op_clamp,
    u"abs": op_abs,
    u"length": op_length,
    u"normalize": op_normalize,
    u"distance": op_distance,
    u"dot": op_dot,
    u"reflect": op_reflect,
    u"refract": op_refract,
    u"^": op_pow,
    u"stringify": op_stringify,
    u"coercion": atom_coercion,
    u"conversion": atom_conversion,
    u"getattr": atom_getattr,
    u"setattr": atom_setattr,
    u"dynamic_getattr": atom_dynamic_getattr,
    u"dynamic_setattr": atom_dynamic_setattr,
}

def get_properties(x):
    if isinstance(x, Kind):
        return x.properties
    if isinstance(x, Constant):
        return x.properties
    if isinstance(x, Atom):
        return x.properties
    if isinstance(x, Builtin):
        return x.properties
    if isinstance(x, Operator):
        return x.properties
    return None
