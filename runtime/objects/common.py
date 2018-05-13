from inspect import getargs
from rpython.rlib import unroll
from rpython.rlib.objectmodel import (
    always_inline,
    compute_hash,
    not_rpython,
    specialize,
)
from rpython.rlib.rarithmetic import intmask

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
        assert False, "abstract method"


# NOPA stands for a non-parametric interface
class InterfaceNOPA(Interface):
    interface = None

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
    def __init__(self):
        self.memo = {}

func_interfaces = FunctionMemo()

def get_function_interface(argc, vari, opt):
    key = (argc, vari, opt)
    try:
        return func_interfaces.memo[key]
    except KeyError:
        face = FunctionInterface(argc, vari, opt)
        func_interfaces.memo[key] = face
        return face

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
    if not isinstance(callee, Builtin):
        raise error(e_TypeError())
    #while not isinstance(callee, Builtin):
    #    args.insert(0, callee)
    #    callee = callee.face().method(op_call)
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
    face = get_function_interface(argc, opt, vari)
    return Builtin(py_bridge, face)

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

# Type error is every error that can be discovered without
# running the program iff the type annotation succeeds.
class e_TypeError(Object):
    pass

# Operators are the next element to be implemented. They
# form the foundations for the object system here.

#class OperatorInterface(FunctionInterface):
#    interface = InterfaceNOPA()
#    def __init__(self, selector, argc, vari, opt):
#        self.selector = selector
#        FunctionInterface.__init__(self, argc, vari, opt)


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
