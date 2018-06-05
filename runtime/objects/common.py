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

    def getattr(self, name):
        raise error(e_TypeError())

    def setattr(self, name):
        raise error(e_TypeError())

    def method(self, operator):
        return operator.resolution_trampoline(self)

# NOPA stands for a non-parametric interface
class InterfaceNOPA(Interface):
    interface = None
    def __init__(self):
        self.methods = {}
        self.getters = {}
        self.setters = {}

    def getattr(self, name):
        impl = self.getters.get(name, None)
        if impl is None:
            return Interface.getattr(self, name)
        return impl

    def setattr(self, name):
        impl = self.setters.get(name, None)
        if impl is None:
            return Interface.setattr(self, name)
        return impl

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
            return self.memo[key]
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
    def __init__(self, builtin_func, builtin_face, prefill=[]):
        self.builtin_func = builtin_func
        self.builtin_face = builtin_face
        self.prefill = prefill

    def face(self):
        return self.builtin_face

# Every call made by the interpreter eventually must resolve
# to a builtin command.
def call(callee, args):
    while not isinstance(callee, Builtin):
        args.insert(0, callee)
        callee = callee.face().method(op_call)
    return callee.builtin_func(callee.prefill + args)

# In few places in the runtime we have to provide "closures" for
# builtin functions. I added the functionality into the builtin objects.
def prefill(builtin, args):
    face = builtin.builtin_face
    argc = face.argc - 1
    vari = face.vari
    opt = min(argc, face.opt)
    return Builtin(
        builtin.builtin_func,
        func_interfaces.get(argc, vari, opt),
        prefill=builtin.prefill + args)

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
    py_bridge.__name__ = function.__name__
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

class e_NoItems(Object):
    pass

class e_NoIndex(Object):
    pass

class e_NoValue(Object):
    pass

class e_AssertTriggered(Object):
    def __init__(self, message):
        self.message = message

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

op_getslot = Operator([0])
op_setslot = Operator([0])

# op_product cannot be a conversion because tuple is not a
# single type but many types.
op_product = Operator([0])

# These may actually be conversion. 'iter' might be as well.
op_pattern = Operator([0]) # case _ of a(...) then ...
#op_form    = Operator([0]) repr(a)

# Some of these are not implemented yet.
#op_shl = Operator([0]) # a << _
#op_shr = Operator([0]) # a >> _

op_cmp = Operator([0,1])
# all comparison operations are derived from the op_cmp

op_concat = Operator([0,1])
op_copy = Operator([0])

op_neg = Operator([0])
op_pos = Operator([0])

op_add = Operator([0,1])
op_sub = Operator([0,1])
op_mul = Operator([0,1])

#op_div = Operator([0,1])
#op_mod = Operator([0,1])
#op_floordiv = Operator([0,1]) # floordiv(a, b)

#op_divrem = Operator([0,1])

op_not = Operator([0])   # ~
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
def method(face, operator, vari=False):
    if not isinstance(face, Interface):
        face = face.interface
    def _impl_(fn):
        face.methods[operator] = python_bridge(fn, vari)
        return fn
    return _impl_

# And the same tools for describing methods.
def getter(face, name, vari=False):
    if not isinstance(face, Interface):
        face = face.interface
    if isinstance(name, str):
        name = name.decode('utf-8')
    def _impl_(fn):
        face.getters[name] = python_bridge(fn, vari)
        return fn
    return _impl_

def setter(face, name, vari=False):
    if not isinstance(face, Interface):
        face = face.interface
    if isinstance(name, str):
        name = name.decode('utf-8')
    def _impl_(fn):
        face.setters[name] = python_bridge(fn, vari)
        return fn
    return _impl_

def attr_method(face, name, vari=False):
    if not isinstance(face, Interface):
        face = face.interface
    if isinstance(name, str):
        name = name.decode('utf-8')
    def _impl_(fn):
        w_fn = python_bridge(fn, vari=vari)
        def _wrapper_(a):
            return prefill(w_fn, [a])
        face.getters[name] = python_bridge(_wrapper_)
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

class InterfaceParametric(InterfaceNOPA):
    def __init__(self, variances):
        self.variances = variances
        self.interface_params = []
        for v in variances:
            if v & 1 != 0:
                self.interface_params.append(TypeParameter(fresh_integer(+1)))
            if v & 2 != 0:
                self.interface_params.append(TypeParameter(fresh_integer(-1)))
            if v & 3 != v:
                raise error(e_TypeError())
        InterfaceNOPA.__init__(self)

# Type parameters are labels returned by interfaces.
class TypeParameter(Object):
    def __init__(self, pol):
        self.pol = cast(pol, Integer)

@method(TypeParameter.interface, op_eq)
def TypeParameter_eq(a, b):
    if a is b:
        return true
    else:
        return false

@method(TypeParameter.interface, op_hash)
def TypeParameter_hash(a):
    return fresh_integer(compute_hash(a))

@getter(TypeParameter.interface, u"pol")
def TypeParameter_get_pol(a):
    return cast(a, TypeParameter).pol

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

    def getattr(self, name):
        if name in self.cells:
            return prefill(w_load_cell, [String(name)])
        else:
            return Interface.getattr(self, name)

    def setattr(self, name):
        if name in self.cells:
            return prefill(w_store_cell, [String(name)])
        else:
            return Interface.setattr(self, name)

class Module(Object):
    interface = None
    def __init__(self):
        self.module_face = ModuleInterface()

    def face(self):
        return self.module_face

    def assign(self, name, value):
        face = self.module_face
        if name in face.cells:
            cell = face.cells[name]
            cell.store(value)
        else:
            self.assign_cell(name, ConstantModuleCell(value))

    def assign_cell(self, name, cell):
        face = self.module_face
        if name in face.cells:
            raise error(e_ModuleError())
        face.cells[name] = cell

    def bind(self, dst, other, src):
        face_dst = self.module_face
        face_src = other.module_face
        if dst in face_dst.cells:
            raise error(e_ModuleError())
        if src not in face_src.cells:
            raise error(e_TypeError())
        face_dst.cells[dst] = face_src.cells[src]

@builtin()
def w_load_cell(name, module):
    face = cast(module.face(), ModuleInterface)
    name = cast(name, String).string_val
    return face.cells[name].load()

@builtin()
def w_store_cell(name, module, value):
    face = cast(module.face(), ModuleInterface)
    name = cast(name, String).string_val
    face.cells[name].store(value)

class ModuleCell:
    def load(self):
        raise error(e_TypeError())

    def store(self, value):
        raise error(e_TypeError())

class ConstantModuleCell(ModuleCell):
    def __init__(self, val):
        self.val = val

    def load(self):
        return self.val

    def store(self, value):
        raise error(e_TypeError())

class ModuleSpace(Object):
    def __init__(self, local, env, loader, parent=None):
        self.local = local
        self.env = env
        self.loader = loader
        self.parent = parent
        self.loaded = {}

    def is_closed(self):
        return self.loader is None

@builtin()
def w_import(mspace, w_name):
    mspace = cast(mspace, ModuleSpace)
    name = cast(w_name, String).string_val
    if name in mspace.loaded:
        module = mspace.loaded[name]
        if module is None:
            raise error(e_ModuleError()) # disallow recursion.
        return module
    if mspace.is_closed():
        raise error(e_ModuleError())
    mspace.loaded[name] = None # Ensure recursion is catched.
    try:
        module = call(mspace.loader, [mspace, w_name])
    finally:
        mspace.loaded.pop(name)
    mspace.loaded[name] = module
    return module

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

@method(Iterator.interface, op_iter)
def Iterator_iter(a):
    return a

# Tuples form the basis for records and they appear in function
# definitions a bit too.
class TupleInterface(Interface):
    def __init__(self, arity):
        self.arity = arity

    def method(self, operator):
        if operator is op_product:
            return w_return_itself
        if operator is op_hash:
            return w_tuple_hash
        if operator is op_eq:
            return w_tuple_eq
        return Interface.method(self, operator)

w_return_itself = python_bridge(lambda a: a)

# Further introduction of methods that operate on
# many shapes of one variation of a type
# may require some sort of type constructors.
@python_bridge
def w_tuple_hash(a):
    contents = cast(a, Tuple).tuple_val
    mult = 1000003
    x = 0x345678
    z = len(contents)
    for item in contents:
        y = cast(call(op_hash, [item]), Integer).toint()
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return fresh_integer(intmask(x))

@python_bridge
def w_tuple_eq(a, b):
    a = cast(a, Tuple).tuple_val
    b = cast(b, Tuple).tuple_val
    if len(a) != len(b):
        return false
    for i in range(len(a)):
        if convert(call(op_eq, [a[i], b[i]]), Bool) is false:
            return false
    return true

# Just like functions, tuples have parameters in their interfaces,
# and we have to memoize them by those parameters.
class TupleMemo:
    def __init__(self):
        self.memo = {}

    def get(self, arity):
        try:
            return self.memo[arity]
        except KeyError:
            face = TupleInterface(arity)
            self.memo[arity] = face
            return face

tuple_interfaces = TupleMemo()

class Tuple(Object):
    interface = None
    def __init__(self, tuple_val):
        self.tuple_val = tuple_val
        self.tuple_face = tuple_interfaces.get(len(tuple_val))

    def face(self):
        return self.tuple_face

# If the type is parametric, this probably is a type constructor
# and not an interface, but lets get some
# results first and afterwards make it correct.

# It is certain that this section of the code will see more changes
# in short time. 
def new_datatype(varc):
    return Datatype(varc)

# This is probably going to need a datatype that has
# parameters and one that does not have them.
class Datatype(Interface):
    def __init__(self, varc):
        self.varc = varc
        self.closed = False
        self.constants = []
        self.constructors = []
        self.methods = {}
        self.getters = {}
        self.setters = {}
        self.datatype_labels = {}

    def close(self):
        self.closed = True

    def method(self, operator):
        impl = self.methods.get(operator, None)
        if impl is None:
            return Interface.method(self, operator)
        return impl

    def getattr(self, name):
        if name in self.datatype_labels:
            return prefill(w_tagu_accessor, [String(name)])
        impl = self.getters.get(name, None)
        if impl is None:
            return Interface.getattr(self, name)
        return impl

    def setattr(self, name):
        impl = self.setters.get(name, None)
        if impl is None:
            return Interface.setattr(self, name)
        return impl

def add_method(datatype, op, method):
    datatype.methods[op] = method

def add_attr(datatype, name, method, is_setter):
    if is_setter:
        datatype.setters[name] = method
    else:
        datatype.getters[name] = method

def add_attr_method(datatype, name, method):
    datatype.getters[name] = Curry(method, [], 1)

# Attribute methods need to add some parameters every
# once and then.
class Curry(Object):
    def __init__(self, function, args, count):
        self.curry_function = function
        self.curry_args = args
        self.curry_count = count

@method(Curry.interface, op_call, vari=True)
def Curry_call(a, args):
    a = cast(a, Curry)
    if a.curry_count < 0:
        return call(a.curry_function, a.curry_args + args)
    if a.curry_count != len(args):
        raise error(e_TypeError())
    return Curry(a.curry_function, args, -1)

# We are going to need the constructors to determine the variance
# of our new datatype.

# Also proposing: if an object has bivariants or contravariants, then
# it cannot have conversions.

@method(Datatype.interface, op_call, vari=True)
def Datatype_call(datatype, args):
    datatype = cast(datatype, Datatype)
    if datatype.varc != len(args):
        raise error(e_TypeError())
    return TypeInstance(datatype, args)

@method(InterfaceParametric.interface, op_call, vari=True)
def InterfaceParametric_call(datatype, args):
    datatype = cast(datatype, InterfaceParametric)
    if len(datatype.variances) != len(args):
        raise error(e_TypeError())
    return TypeInstance(datatype, args)

class TypeInstance(Object):
    def __init__(self, datatype, args):
        self.datatype = datatype
        self.args = args

class Freevar(Object):
    def __init__(self, index):
        self.index = index

def new_constant(datatype):
    if datatype.closed:
        raise error(e_EvalError())
    const = Constant(datatype)
    datatype.constants.append(const)
    return const
    
def new_constructor(datatype, params, labels):
    if datatype.closed:
        raise error(e_EvalError())
    cons = Constructor(datatype, params, labels)
    datatype.constructors.append(cons)
    for label in labels:
        datatype.datatype_labels[label] = None
    return cons

class Constructor(Object):
    def __init__(self, datatype, fields, cons_labels):
        self.datatype = datatype
        self.fields = fields
        self.cons_labels = cons_labels

@method(Constructor.interface, op_call, vari=True)
def Constructor_call(constructor, fields):
    # TODO: Check the fields.
    return TaggedUnion(constructor, fields)

@method(Constructor.interface, op_pattern)
def Constructor_pattern(constructor):
    check = prefill(w_tagu_check, [constructor])
    unpack = prefill(w_tagu_unpack, [constructor])
    return Tuple([check, unpack])

@python_bridge
def w_tagu_check(constructor, tagu):
    constructor = cast(constructor, Constructor)
    tagu = convert(tagu, constructor.datatype)
    if tagu.tagu_cons is constructor:
        return true
    else:
        return false

@python_bridge
def w_tagu_unpack(constructor, tagu):
    constructor = cast(constructor, Constructor)
    tagu = convert(tagu, constructor.datatype)
    return Tuple(cast(tagu, TaggedUnion).fields)

@python_bridge
def w_tagu_accessor(name, tagu):
    tagu = cast(tagu, TaggedUnion)
    name = cast(name, String).string_val
    try:
        return tagu.fields[tagu.tagu_cons.cons_labels[name]]
    except KeyError:
        raise error(e_PartialOnArgument())

class TaggedUnion(Object):
    interface = None
    def __init__(self, tagu_cons, fields):
        self.tagu_cons = tagu_cons
        self.fields = fields

    def face(self):
        return self.tagu_cons.datatype

# Provides hashtables to equality and hash.
def eq_fn(a, b):
    result = convert(call(op_eq, [a,b]), Bool)
    if result is true:
        return True
    else:
        return False

def hash_fn(a):
    result = call(op_hash, [a])
    return intmask(cast(result, Integer).toint())

# For some purposes we need type parameter groups.
def make_parameter_group():
    class TypeParameterGroup:
        def __init__(self, pol):
            self.pol = pol
            self.memo = {}

        def get(self, index):
            try:
                return self.memo[index]
            except KeyError as _:
                param = TypeParameter(self.pol)
                self.memo[index] = param
                return param
    return TypeParameterGroup

TypeParameterIndexGroup = make_parameter_group()
TypeParameterNameGroup = make_parameter_group()

# All functions have same type parameters.
cod = TypeParameter(fresh_integer(+1))
dom = TypeParameterIndexGroup(fresh_integer(-1))
dom_vari = TypeParameterIndexGroup(fresh_integer(-1))

@attr_method(FunctionInterface.interface, u"format")
def FunctionInterface_format(f, px, prefix=None):
    f = cast(f, FunctionInterface)
    out = []
    for i in range(f.argc-f.opt):
        text = call(op_getitem, [px, dom.get(i)])
        out.append(cast(text, String).string_val)
    for i in range(f.argc-f.opt, f.argc):
        text = call(op_getitem, [px, dom.get(i)])
        out.append(cast(text, String).string_val + u"?")
    if f.vari:
        text = call(op_getitem, [px, dom_vari.get(f.argc)])
        out.append(cast(text, String).string_val + u"...")
    text = call(op_getitem, [px, cod])
    signature = u"(" + u", ".join(out) + u") -> " + cast(text, String).string_val
    if prefix is not None:
        prefix = cast(prefix, String).string_val
        return String(prefix + u"(" + signature + u")")
    return String(signature)

@attr_method(BuiltinInterface.interface, u"format")
def BuiltinInterface_format(f, px):
    return FunctionInterface_format(f, px, String(u"builtin"))

@attr_method(FunctionInterface.interface, u"params")
@attr_method(BuiltinInterface.interface, u"params")
def FunctionInterface_params(f):
    f = cast(f, FunctionInterface)
    out = []
    for i in range(f.argc):
        out.append(dom.get(i))
    if f.vari:
        out.append(dom_vari.get(f.argc))
    out.append(cod)
    return List(out)

@method(FunctionInterface.interface, op_eq)
@method(BuiltinInterface.interface, op_eq)
def FunctionInterface_eq(a, b):
    return true if a is b else false

@method(FunctionInterface.interface, op_hash)
@method(BuiltinInterface.interface, op_hash)
def FunctionInterface_hash(a):
    return fresh_integer(compute_hash(a))

@attr_method(InterfaceNOPA.interface, u"params")
def NOPA_params(n):
    return List([])

@attr_method(InterfaceNOPA.interface, u"format")
def InterfaceNOPA_format(f, px):
    # TODO: Module names should be implemented next.
    prefix = cast(call(op_stringify, [f]), String).string_val
    return String(prefix)

@method(FunctionInterface.interface, op_eq)
@method(BuiltinInterface.interface, op_eq)
def NOPA_eq(a, b):
    return true if a is b else false

@method(InterfaceNOPA.interface, op_hash)
def NOPA_hash(a):
    return fresh_integer(compute_hash(a))

@attr_method(InterfaceParametric.interface, u"params")
def InterfaceParametric_params(a):
    return List(cast(a, InterfaceParametric).interface_params)

@attr_method(InterfaceParametric.interface, u"format")
def InterfaceParametric_format(f, px):
    f = cast(f, InterfaceParametric)
    out = []
    i = 0
    for v in f.variances:
        if v & 3 != 0:
            neg = call(op_getitem, [px, f.interface_params[i+0]])
            pos = call(op_getitem, [px, f.interface_params[i+1]])
            n = cast(neg, String).string_val
            p = cast(pos, String).string_val
            out.append(u"{-" + n + u", +" + p + u"}")
            i += 2
        elif v & 1 != 0:
            pos = call(op_getitem, [px, f.interface_params[i]])
            out.append(cast(pos, String).string_val)
            i += 1
        elif v & 2 != 0:
            neg = call(op_getitem, [px, f.interface_params[i]])
            out.append(cast(neg, String).string_val)
            i += 1
        if v & 3 != v:
            raise error(e_TypeError())
    # TODO: Module names should be implemented next.
    prefix = cast(call(op_stringify, [f]), String).string_val
    return String(prefix + u"(" + u", ".join(out) + u")")

@method(InterfaceParametric.interface, op_eq)
def InterfaceParametric_eq(a, b):
    return true if a is b else false

@method(InterfaceParametric.interface, op_hash)
def InterfaceParametric_hash(a):
    return fresh_integer(compute_hash(a))

# Likewise, all records have their own parameter groups.
attr_p = TypeParameterNameGroup(fresh_integer(+1))
attr_n = TypeParameterNameGroup(fresh_integer(-1))

# Temporary measure to see what is going on.
def Any_stringify(a):
    return String(a.__class__.__name__.decode('utf-8'))
op_stringify.default = builtin()(Any_stringify)

# Derivators are functions that produce methods for datatypes
# by some predefined rule.
@python_bridge
def w_by_reference(datatype, op):
    if op is op_eq:
        return w_eq_by_reference
    elif op is op_hash:
        return w_hash_by_reference
    else:
        raise error(e_PartialOnArgument())

@python_bridge
def w_eq_by_reference(a, b):
    if a is b:
        return true
    else:
        return false

@python_bridge
def w_hash_by_reference(a):
    return fresh_integer(compute_hash(a))

@python_bridge
def w_by_value(datatype, op):
    if op is op_eq:
        return w_eq_by_value
    elif op is op_hash:
        return w_hash_by_value
    else:
        raise error(e_PartialOnArgument())

@python_bridge
def w_eq_by_value(a, b):
    a = cast(a, TaggedUnion)
    b = cast(b, TaggedUnion)
    if not (a.tagu_cons is b.tagu_cons):
        return false
    for i in range(len(a.fields)):
        if call(op_eq, [a.fields[i], b.fields[i]]) is false:
            return false
    return true

@python_bridge
def w_hash_by_value(a):
    a = cast(a, TaggedUnion)
    mult = 1000003
    x = 0x345678
    z = len(a.fields)
    for item in a.fields:
        y = cast(call(op_hash, [item]), Integer).toint()
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return fresh_integer(intmask(x))
