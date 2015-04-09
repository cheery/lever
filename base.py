from space import *
import api
import ffi
import os

# The base environment

module = Module('base', {
    'module': Module.interface,
    'object': Object.interface,
    'list': List.interface,
    'multimethod': Multimethod.interface,
    'int': Integer.interface,
    'bool': Boolean.interface,
    'str': String.interface,
    'null': null,
    'true': true,
    'false': false,

    # Doesn't belong here.
    'api': api.module,
    'ffi': ffi.module,
}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_')
    module.namespace[name] = Builtin(fn, name)
    return fn

@builtin
def interface(argv):
    if len(argv) != 1:
        raise Error("interface expects 1 argument, got " + str(len(argv)))
    return argv[0].interface

#def pyl_apply(argv):
#    N = len(argv) - 1
#    assert N >= 1
#    args = argv[1:N]
#    varg = argv[N]
#    assert isinstance(varg, List)
#    return argv[0].invoke(args + varg.items)

@builtin
@signature(Object, Object)
def getitem(obj, index):
    return obj.getitem(index)

@builtin
@signature(Object, Object, Object)
def setitem(obj, index, value):
    return obj.setitem(index, value)

@builtin
@signature(Object, String)
def getattr(obj, index):
    return obj.getattr(index.string)

@builtin
@signature(Object, String, Object)
def setattr(obj, index, value):
    return obj.setattr(index.string, value)

#def pyl_callattr(argv):
#    assert len(argv) >= 2
#    name = argv[1]
#    assert isinstance(name, String)
#    return argv[0].callattr(name.string, argv[2:len(argv)])

@builtin
def print_(argv):
    space = ''
    for arg in argv:
        if isinstance(arg, String):
            string = arg.string
        else:
            string = arg.repr()
        os.write(1, space + string)
        space = ' '
    os.write(1, '\n')
    return null

#@global_builtin('read-file')
#def pyl_read_file(argv):
#    assert len(argv) >= 1
#    arg0 = argv.pop(0)
#    assert isinstance(arg0, String)
#    return read_file(arg0.string)

# And and or are macros in the compiler. These are
# convenience functions, likely not often used.
# erm. Actually 'and' function is used by chaining.
@builtin
@signature(Object, Object)
def and_(a, b):
    return boolean(is_true(a) and is_true(b))

@builtin
@signature(Object, Object)
def or_(a, b):
    return boolean(is_true(a) or is_true(b))

@builtin
@signature(Object)
def not_(a):
    return boolean(is_false(a))

module.namespace['coerce'] = coerce = Multimethod(2)
@coerce.multimethod_s(Boolean, Boolean)
def _(a, b):
    return List([Integer(int(a.flag)), Integer(int(b.flag))])

@coerce.multimethod_s(Integer, Boolean)
def _(a, b):
    return List([a, Integer(int(b.flag))])

@coerce.multimethod_s(Boolean, Integer)
def _(a, b):
    return List([Integer(int(a.flag)), b])

def arithmetic_multimethod(operation):
    method = Multimethod(2)
    @Builtin
    def default(argv):
        args = coerce.call(argv)
        assert isinstance(args, List)
        return method.call_suppressed(args.contents)
    method.default = default
    @method.multimethod_s(Integer, Integer)
    def _(a, b):
        return Integer(operation(a.value, b.value))
    return method

module.namespace['+'] = arithmetic_multimethod(lambda a, b: a + b)
module.namespace['-'] = arithmetic_multimethod(lambda a, b: a - b)
module.namespace['*'] = arithmetic_multimethod(lambda a, b: a * b)
module.namespace['/'] = arithmetic_multimethod(lambda a, b: a / b)
module.namespace['|'] = arithmetic_multimethod(lambda a, b: a | b)
module.namespace['&'] = arithmetic_multimethod(lambda a, b: a & b)
module.namespace['^'] = arithmetic_multimethod(lambda a, b: a ^ b)
module.namespace['<<'] = arithmetic_multimethod(lambda a, b: a << b)
module.namespace['>>'] = arithmetic_multimethod(lambda a, b: a >> b)
module.namespace['min'] = arithmetic_multimethod(lambda a, b: min(a, b))
module.namespace['max'] = arithmetic_multimethod(lambda a, b: max(a, b))

# Not actual implementations of these functions
# All of these will be multimethods
@signature(Integer, Integer)
def cmp_lt(a, b):
    return boolean(a.value < b.value)
module.namespace['<'] = Builtin(cmp_lt, '<')

@signature(Integer, Integer)
def cmp_gt(a, b):
    return boolean(a.value > b.value)
module.namespace['>'] = Builtin(cmp_gt, '>')

@signature(Integer, Integer)
def cmp_le(a, b):
    return boolean(a.value <= b.value)
module.namespace['<='] = Builtin(cmp_le, '<=')

@signature(Integer, Integer)
def cmp_ge(a, b):
    return boolean(a.value >= b.value)
module.namespace['>='] = Builtin(cmp_ge, '>=')

module.namespace['!='] = ne = Multimethod(2)
@signature(Object, Object)
def ne_default(a, b):
    return boolean(a != b)
ne.default = Builtin(ne_default)

@ne.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value != b.value)

module.namespace['=='] = eq = Multimethod(2)
@signature(Object, Object)
def eq_default(a, b):
    return boolean(a == b)
eq.default = Builtin(eq_default)

@eq.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value == b.value)

module.namespace['-expr'] = neg = Multimethod(1)
@neg.multimethod_s(Integer)
def _(a):
    return Integer(-a.value)

module.namespace['+expr'] = pos = Multimethod(1)
@pos.multimethod_s(Integer)
def _(a):
    return Integer(+a.value)
