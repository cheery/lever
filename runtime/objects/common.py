from inspect import getargs
from rpython.rlib import unroll
from rpython.rlib.objectmodel import (
    always_inline,
    compute_hash,
    not_rpython,
    specialize,
)
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rbigint import rbigint

# Objects in a dynamically typed system is a large
# union of tagged records. RPython requires that a
# this common superclass is provided for all objects that
# the user can access from within the runtime.
class Object:
    interface = None
    # If an object does not specify an interface, it is assumed
    # that the object is simple, nonparametric.
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if 'interface' not in dict:
                cls.interface = InterfaceNOPA()

    # .face() is the only method that is common for every
    # object in the system because the method resolution
    # occurs entirely within the interface.
    def face(self):
        return self.__class__.interface

# Resolving methods on interfaces help to ensure that
# interface block corresponds with the type of an object.
class Interface(Object):
    interface = None

    def method(self, operator):
        return operator.resolution_trampoline(self)

# NOPA stands for a non-parametric interface
class InterfaceNOPA(Interface):
    interface = None
    def __init__(self):
        self.methods = {}

    def method(self, operator):
        impl = self.methods.get(operator, None)
        if impl is None:
            return Interface.method(self, operator)
        return impl

# The object should never return itself as a face, but
# we have to cut our type hierarchy to something. We do it
# when there is no longer any type information present in the type.
InterfaceNOPA.interface = InterfaceNOPA()

# An alternative to this would be to produce an interface of
# an interface, which is numbered by how many times 'face'
# has been called.

# There are several interfaces that refer only to constants,
# we start by defining them because they're easiest to define.
class Constant(Object):
    interface = None
    def __init__(self, constant_face):
        self.constant_face = constant_face
    
    def face(self):
        return self.constant_face

# A function may return 'null'. Like saying 'never', it
# implies that there is no information transmitted in the
# value that is passed around.
Unit = InterfaceNOPA()
null = Constant(Unit)

Bool = InterfaceNOPA()
true  = Constant(Bool)
false = Constant(Bool)

class Integer(Object):
    def __init__(self, integer_val):
        self.integer_val = integer_val

    # TODO: better error message for this?
    def toint(self):
        try:
            return self.integer_val.toint()
        except OverflowError:
            raise error(e_OverflowError())

# 
def fresh_integer(val):
    return Integer(rbigint.fromint(val))

class String(Object):
    def __init__(self, string_val):
        self.string_val = string_val

# The next interface binds callsites to functions.
# argc tells how many arguments there are.
# vari tells if variadic number of arguments are accepted.
# opt tells how many of the arguments are optional.
# On callsites the opt must be 0.
class FunctionInterface(Interface):
    interface = InterfaceNOPA()
    def __init__(self, argc, vari, opt):
        self.argc = argc
        self.vari = vari
        self.opt = opt

# Instances of function interfaces have somewhat special
# meaning and there will be finite amount of them, so
# every produced instance will be memoized so that they
# are shared between functions that have the same shape.
class FunctionMemo:
    def __init__(self, cls):
        self.memo = {}
        self.cls = cls

    def get(self, argc, vari, opt):
        key = (argc, vari, opt)
        try:
            return func_interfaces.memo[key]
        except KeyError:
            face = self.cls(argc, vari, opt)
            self.memo[key] = face
            return face

func_interfaces = FunctionMemo(FunctionInterface)

class BuiltinInterface(FunctionInterface):
    def method(self, op):
        if op is op_call:
            return w_call
        return FunctionInterface.method(self, op)

builtin_interfaces = FunctionMemo(BuiltinInterface)

# To compute with functions you eventually need concretely
# defined functions on the bottom. Builtins serve this
# purpose.
class Builtin(Object):
    interface = None
    def __init__(self, builtin_func, builtin_face):
        self.builtin_func = builtin_func
        self.builtin_face = builtin_face

    def face(self):
        return self.builtin_face

# Every call made by the interpreter eventually must resolve
# to a builtin command.
def call(callee, args):
    while not isinstance(callee, Builtin):
        args.insert(0, callee)
        callee = callee.face().method(op_call)
    return callee.builtin_func(args)

# This decorator replaces the function with a builtin
# representing that function. This is likely not going to be
# used much because it makes it harder to access the
# function from within other builtins.
def builtin(vari=False):
    def _impl_(func):
        return python_bridge(func, vari)
    return _impl_

# The runtime uses lists to pass values in a call, but
# this bridges it with the Python calling conventions.
# This way every builtin does not need to retrieve their
# arguments from lists in the beginning of the program.
@not_rpython
def python_bridge(function, vari=False):
    args, varargs, keywords = getargs(function.__code__)
    defaults = function.__defaults__ or ()
    argc = max(len(args) - int(vari), 0)
    opt = max(len(defaults) - int(vari), 0)
    argi = unroll.unrolling_iterable(range(argc-opt))
    argj = unroll.unrolling_iterable(range(argc-opt, argc))
    def py_bridge(argv):
        args = ()
        length = len(argv)
        if length < argc - opt:
            raise error(e_TypeError())
        if argc < length and not vari:
            raise error(e_TypeError())
        for i in argi:
            args += (argv[i],)
        for i in argj:
            if i < length:
                args += (argv[i],)
            else:
                args += (defaults[i+opt-argc],)
        if vari:
            args += (argv[min(argc, length):],)
        result = function(*args)
        if result is None:
            return null
        return result
    face = builtin_interfaces.get(argc, opt, vari)
    return Builtin(py_bridge, face)

# If the builtin ends up being called through op_call,
# it needs an access to this raw operation in order to
# resolve.
w_call = python_bridge(call, vari=True)

# Many of the builtin functions still require specific
# records or group of records that we have to provide them.
# We can convert the object through subtyping into the form
# that it is needed in.
@specialize.arg(1)
def cast(obj, cls):
    if isinstance(obj, cls):
        return obj
    # For now though, we do not have any conversion
    # semantics.
    raise error(e_TypeError())

# Being able to call functions present a possibility that we
# get errors, in the earlier designs I introduced this
# machinery too late and it caused issues. So this is the
# right time and place to introduce errors.
def error(response):
    return Traceback(response)

# The traceback frame is required by RPython, but the
# shape of the error responses will be probably limited
# anyway. 
class Traceback(Exception):
    def __init__(self, error):
        self.error = error
        self.trace = []

# Type error is every error that can be discovered without
# running the program iff the type annotation succeeds.
class e_TypeError(Object):
    pass

# Appears in the runtime/json_loader.py the first time
class e_IOError(Object):
    pass

class e_JSONDecodeError(Object):
    def __init__(self, message):
        self.message = message

class e_IntegerParseError(Object):
    pass

class e_OverflowError(Object):
    pass

class e_ModuleError(Object):
    pass

class e_EvalError(Object):
    pass

class e_IntegerBaseError(Object):
    pass

class e_PartialOnArgument(Object):
    pass

# Operators are the next element to be implemented. They
# form the foundations for the whole object system here.
class OperatorInterface(Interface): 
    def __init__(self, operator):
        self.operator = operator

    def method(self, operator):
        if operator is op_call:
            return w_operator_call
        return Interface.method(self, operator)

# Every operator has an unique type, but generally they are
# callable and try to resolve themselves based on the
# arguments they receive.
class Operator(Object):
    def __init__(self, selectors):
        self.operator_face = OperatorInterface(self)
        self.selectors = selectors
        self.default = None
        self.methods = {}

        self.min_arity = 0
        for index in selectors:
            self.min_arity = max(self.min_arity, index + 1)

    def face(self):
        return self.operator_face

    # When user defines new operators he may need to
    # provide methods for existing types. This is the last
    # place that is checked though, because I am expecting
    # that new types are more common than new operators.
    def resolution_trampoline(self, interface):
        impl = self.methods.get(interface, self.default)
        if impl is None:
            raise error(e_TypeError())
        return impl

# Equality and hashing is crucial for dictionaries and sets.
op_eq = Operator([0, 1])
def op_eq_default(a, b):
    if a is b:
        return true
    return false
op_eq.default = python_bridge(op_eq_default)

op_hash = Operator([0])

# Without the call operator we would be unable to provide
# closures that can be called.
op_call = Operator([0])

# op_call is slightly more special than others because it
# corresponds with the 'call' -function here. The 'call' is
# actually called by the interpreter, but it corresponds
# with the 'op_call'.

# All the remaining operators defined by the runtime are not
# as important for proper functioning of the runtime, but
# without them the runtime would not have much it can do.

op_in = Operator([1])
op_getitem = Operator([0])
op_setitem = Operator([0])
op_iter = Operator([0])

# These may actually be conversion. 'iter' might be as well.
#op_product = Operator([0]) x,y = a
#op_pattern = Operator([0]) case _ of a(...) then ...
#op_form    = Operator([0]) repr(a)

# Some of these are not implemented yet.
#op_shl = Operator([0]) # a << _
#op_shr = Operator([0]) # a >> _

op_cmp = Operator([0,1])
# all comparison operations are derived from the op_cmp

op_concat = Operator([0,1])

#op_neg = Operator([0])
#op_pos = Operator([0])

op_add = Operator([0,1])
op_sub = Operator([0,1])
op_mul = Operator([0,1])

#op_div = Operator([0,1])
#op_mod = Operator([0,1])
#op_floordiv = Operator([0,1]) # floordiv(a, b)

#op_divrem = Operator([0,1])

op_and = Operator([0,1]) # &
op_or  = Operator([0,1]) # |
op_xor = Operator([0,1]) # xor(a,b)


#op_clamp = Operator([0]) clamp(a, min,max)
#op_abs = Operator([0])
#op_length = Operator([0])
#op_normalize = Operator([0])
#op_distance = Operator([0,1])
#op_dot = Operator([0,1])
#op_reflect = Operator([0,1])
#op_refract = Operator([0,1]) refract(a,b,eta)
#op_pow = Operator([0,1])

# Stringify is provided so that we can print and show
# values. I don't think it's a conversion because many
# things stringifyable have nothing else to do with strings.
op_stringify = Operator([0])


# Every operator is resolved by selectors, in the same
# manner. If the interface doesn't provide an
# implementation, it will attempt to obtain implementation
# for itself from the operator itself.
def operator_call(op, args):
    L = len(op.selectors)
    if len(args) < op.min_arity:
        raise error(e_TypeError())
    if L == 1:
        index = op.selectors[0]
        impl = args[index].face().method(op)
    else:
        faces = {}
        for index in op.selectors:
            faces[args[index].face()] = None
        face = unique_coercion(faces)
        if face is None:
            raise error(e_TypeError())
        impl = face.method(op)
        args = list(args)
        for index in op.selectors:
            args[index] = convert(args[index], face)
    return call(impl, args)
w_operator_call = python_bridge(operator_call, vari=True)

# Helper decorator for describing new operators
def method(face, operator):
    def _impl_(fn, vari=False):
        face.methods[operator] = python_bridge(fn, vari)
        return fn
    return _impl_

# The operator handling needs operative coercion
def unique_coercion(faces):
    s = []
    for y in faces:
        ok = True
        for x in faces:
            ok = ok and (x == y or has_coercion(x, y))
        if ok:
            s.append(y)
    if len(s) == 1:
        return s[0]
    return None

# For now we do not have any conversion&coercion utilities
# in place.
def has_coercion(x, y):
    return False

def convert(x, face):
    if x.face() is not face:
        raise error(e_TypeError())
    return x

# The important concept in this new object system is the
# variances of different kinds. First we have parametric
# variance such as here.
INV = INVARIANT     = 0
COV = COVARIANT     = 1
CNV = CONTRAVARIANT = 2
BIV = BIVARIANT     = 3

class InterfaceParametric(Interface):
    def __init__(self, variances):
        self.variances = variances

# If we provide R/W flags, we can make these structures
# immutable, but it would be hard to ensure such constraints
# statically in the type system.
class List(Object):
    interface = InterfaceParametric([BIV])
    def __init__(self, list_val):
        self.list_val = list_val

class Dict(Object):
    interface = InterfaceParametric([BIV, BIV])
    def __init__(self, dict_val):
        self.dict_val = dict_val

class Set(Object):
    interface = InterfaceParametric([BIV])
    def __init__(self, set_val):
        self.set_val = set_val

# Each module becomes their own interface, the system has
# been purposefully designed such that you get an access to
# a new module only after it has been populated.
class ModuleInterface(Interface):
    def __init__(self):
        self.cells = {}

class Module(Object):
    interface = None
    def __init__(self):
        self.module_face = ModuleInterface()

    def face(self):
        return self.module_face

    def assign(self, name, value):
        face = self.module_face
        if name in face.cells:
            raise error(e_ModuleError())
        face.cells[name] = ModuleCell(value)

class ModuleCell:
    def __init__(self, val):
        self.val = val

# Ending the common -module by defining equality and hash
# methods for Unit. These are defined in case there are
# datasets or structures that use null.
@method(Unit, op_eq)
def Unit_eq(a, b):
    return true

@method(Unit, op_hash)
def Unit_hash(a):
    return fresh_integer(0)

@method(Unit, op_stringify)
def Unit_stringify(a):
    return String(u"null")

# The Iterator doesn't return StopIteration() for any
# particular reason. If you use this as an empty iterator,
# make sure you rename it.
class Iterator(Object):
    interface = InterfaceParametric([COV])
    def next(self):
        raise StopIteration()

# Provides hashtables to equality and hash.
def eq_fn(a, b):
    result = convert(call(op_eq, [a,b]), Bool)
    if result is true:
        return true
    else:
        return false

def hash_fn(a):
    result = call(op_hash, [a])
    return intmask(cast(result, Integer).toint())
