from space import *
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

#def pyl_getitem(argv):
#    assert len(argv) == 2
#    return argv[0].getitem(argv[1])
#
#def pyl_setitem(argv):
#    assert len(argv) == 3
#    return argv[0].setitem(argv[1], argv[2])
#
#def pyl_getattr(argv):
#    assert len(argv) == 2
#    name = argv[1]
#    assert isinstance(name, String)
#    return argv[0].getattr(name.string)
#
#def pyl_setattr(argv):
#    assert len(argv) == 3
#    name = argv[1]
#    assert isinstance(name, String)
#    return argv[0].setattr(name.string, argv[2])
#
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
#
#@global_builtin('!=')
#def pyl_equals(argv):
#    assert len(argv) == 2
#    arg0 = argv[0]
#    arg1 = argv[1]
#    if isinstance(arg0, Integer) and isinstance(arg1, Integer):
#        if arg0.value == arg1.value:
#            return false
#        return true
#    if arg0 is arg1:
#        return false
#    else:
#        return true
#
#@global_builtin('==')
#def pyl_equals(argv):
#    assert len(argv) == 2
#    arg0 = argv[0]
#    arg1 = argv[1]
#    if isinstance(arg0, Integer) and isinstance(arg1, Integer):
#        if arg0.value == arg1.value:
#            return true
#        return false
#    if arg0 is arg1:
#        return true
#    else:
#        return false
#
#@global_builtin('and')
#def pyl_and(argv):
#    assert len(argv) == 2
#    arg0 = argv[0]
#    arg1 = argv[1]
#    if is_false(arg0) or is_false(arg1):
#        return false
#    else:
#        return true
#
#@global_builtin('or')
#def pyl_or(argv):
#    assert len(argv) == 2
#    arg0 = argv[0]
#    arg1 = argv[1]
#    if is_false(arg0) and is_false(arg1):
#        return false
#    else:
#        return true
#
#@global_builtin('not')
#def pyl_not(argv):
#    assert len(argv) == 1
#    arg0 = argv[0]
#    if is_false(arg0):
#        return true
#    else:
#        return false
#
#def binary_comparison(name, op):
#    def _impl_(argv):
#        assert len(argv) == 2
#        arg0 = argv[0]
#        arg1 = argv[1]
#        if isinstance(arg0, Integer) and isinstance(arg1, Integer):
#            if op(arg0.value, arg1.value):
#                return true
#            else:
#                return false
#        raise Exception("cannot i" + name + " " + arg0.repr() + " and " + arg1.repr())
#    global_builtin(name)(_impl_)

module.namespace['coerce'] = coerce = Multimethod(2)
@coerce.multimethod(Boolean, Boolean)
def _(argv):
    a = argv[0]
    b = argv[1]
    assert isinstance(a, Boolean)
    assert isinstance(b, Boolean)
    return List([Integer(int(a.flag)), Integer(int(b.flag))])

@coerce.multimethod(Integer, Boolean)
def _(argv):
    a = argv[0]
    b = argv[1]
    assert isinstance(a, Integer)
    assert isinstance(b, Boolean)
    return List([a, Integer(int(b.flag))])

@coerce.multimethod(Boolean, Integer)
def _(argv):
    a = argv[0]
    b = argv[1]
    assert isinstance(a, Boolean)
    assert isinstance(b, Integer)
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
        a = argv[0]
        b = argv[1]
        assert isinstance(a, Integer)
        assert isinstance(b, Integer)
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

#binary_comparison('<', lambda a, b: a < b)
#binary_comparison('>', lambda a, b: a > b)
#binary_comparison('<=', lambda a, b: a <= b)
#binary_comparison('>=', lambda a, b: a >= b)
#binary_comparison('!=', lambda a, b: a != b)
#binary_comparison('==', lambda a, b: a == b)
