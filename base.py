from space import *
import os

import ffi

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
def getitem(argv):
    obj = argument(argv, 0, Object)
    index = argument(argv, 1, Object)
    return obj.getitem(index)

@builtin
def setitem(argv):
    obj = argument(argv, 0, Object)
    index = argument(argv, 1, Object)
    value = argument(argv, 2, Object)
    return obj.setitem(index, value)

@builtin
def getattr(argv):
    obj = argument(argv, 0, Object)
    index = argument(argv, 1, String)
    return obj.getattr(index.string)

@builtin
def setattr(argv):
    obj = argument(argv, 0, Object)
    index = argument(argv, 1, String)
    value = argument(argv, 2, Object)
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
def and_(argv):
    a = argument(argv, 0, Object)
    b = argument(argv, 1, Object)
    return boolean(is_true(a) and is_true(b))

@builtin
def or_(argv):
    a = argument(argv, 0, Object)
    b = argument(argv, 1, Object)
    return boolean(is_true(a) or is_true(b))

@builtin
def not_(argv):
    return boolean(is_false(argument(argv, 0, Object)))

module.namespace['coerce'] = coerce = Multimethod(2)
@coerce.multimethod(Boolean, Boolean)
def _(argv):
    a = argument(argv, 0, Boolean)
    b = argument(argv, 1, Boolean)
    return List([Integer(int(a.flag)), Integer(int(b.flag))])

@coerce.multimethod(Integer, Boolean)
def _(argv):
    a = argument(argv, 0, Integer)
    b = argument(argv, 1, Boolean)
    return List([a, Integer(int(b.flag))])

@coerce.multimethod(Boolean, Integer)
def _(argv):
    a = argument(argv, 0, Boolean)
    b = argument(argv, 1, Integer)
    return List([Integer(int(a.flag)), b])

def arithmetic_multimethod(operation):
    method = Multimethod(2)
    @Builtin
    def default(argv):
        args = coerce.call(argv)
        assert isinstance(args, List)
        return method.call_suppressed(args.contents)
    method.default = default
    @method.multimethod(Integer, Integer)
    def _(argv):
        a = argument(argv, 0, Integer)
        b = argument(argv, 1, Integer)
        return Integer(operation(a.value, b.value))
    return method

module.namespace['+'] = arithmetic_multimethod(lambda a, b: a + b)
module.namespace['-'] = arithmetic_multimethod(lambda a, b: a - b)
module.namespace['*'] = arithmetic_multimethod(lambda a, b: a * b)
module.namespace['|'] = arithmetic_multimethod(lambda a, b: a | b)
module.namespace['&'] = arithmetic_multimethod(lambda a, b: a & b)
module.namespace['^'] = arithmetic_multimethod(lambda a, b: a ^ b)
module.namespace['<<'] = arithmetic_multimethod(lambda a, b: a << b)
module.namespace['>>'] = arithmetic_multimethod(lambda a, b: a >> b)
module.namespace['min'] = arithmetic_multimethod(lambda a, b: min(a, b))
module.namespace['max'] = arithmetic_multimethod(lambda a, b: max(a, b))

# Not actual implementations of these functions
# All of these will be multimethods
def cmp_lt(argv):
    a = argument(argv, 0, Integer)
    b = argument(argv, 1, Integer)
    return boolean(a.value < b.value)
module.namespace['<'] = Builtin(cmp_lt, '<')

def cmp_gt(argv):
    a = argument(argv, 0, Integer)
    b = argument(argv, 1, Integer)
    return boolean(a.value > b.value)
module.namespace['>'] = Builtin(cmp_gt, '>')

def cmp_le(argv):
    a = argument(argv, 0, Integer)
    b = argument(argv, 1, Integer)
    return boolean(a.value <= b.value)
module.namespace['<='] = Builtin(cmp_le, '<=')

def cmp_ge(argv):
    a = argument(argv, 0, Integer)
    b = argument(argv, 1, Integer)
    return boolean(a.value >= b.value)
module.namespace['>='] = Builtin(cmp_ge, '>=')

module.namespace['!='] = ne = Multimethod(2)
def ne_default(argv):
    a = argument(argv, 0, Object)
    b = argument(argv, 1, Object)
    return boolean(a != b)
ne.default = ne_default

@ne.multimethod(Integer, Integer)
def _(argv):
    a = argument(argv, 0, Integer)
    b = argument(argv, 1, Integer)
    return boolean(a.value != b.value)

module.namespace['=='] = eq = Multimethod(2)
def eq_default(argv):
    a = argument(argv, 0, Object)
    b = argument(argv, 1, Object)
    return boolean(a == b)
eq.default = eq_default
module.namespace['!='] = Builtin(cmp_le, '!=')

@eq.multimethod(Integer, Integer)
def _(argv):
    a = argument(argv, 0, Integer)
    b = argument(argv, 1, Integer)
    return boolean(a.value == b.value)
module.namespace['=='] = Builtin(cmp_ge, '==')
