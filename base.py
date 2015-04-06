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
#def binary_arithmetic(name, op):
#    def _impl_(argv):
#        assert len(argv) == 2
#        arg0 = argv[0]
#        arg1 = argv[1]
#        if isinstance(arg0, Integer) and isinstance(arg1, Integer):
#            return Integer(op(arg0.value, arg1.value))
#        raise Exception("cannot i" + name + " " + arg0.repr() + " and " + arg1.repr())
#    global_builtin(name)(_impl_)
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
#
#global_scope['coerce'] = coerce_method = Multimethod(2, default=None)
#
#@coerce_method.register(Boolean, Integer)
#def coerce_bool_int(argv):
#    if len(argv) != 2:
#        raise Exception("expected exactly 2 arguments")
#    arg0 = argv[0]
#    arg1 = argv[1]
#    assert isinstance(arg0, Boolean)
#    assert isinstance(arg1, Integer)
#    return List([Integer(int(arg0.flag)), arg1])
#
#@coerce_method.register(Integer, Boolean)
#def coerce_bool_int(argv):
#    if len(argv) != 2:
#        raise Exception("expected exactly 2 arguments")
#    arg0 = argv[0]
#    arg1 = argv[1]
#    assert isinstance(arg0, Integer)
#    assert isinstance(arg1, Boolean)
#    return List([arg0, Integer(int(arg1.flag))])
#
#global_scope['+'] = plus_method = Multimethod(2, default=None)
#
#def plus_default(argv):
#    args = coerce_method.invoke(argv)
#    assert isinstance(args, List)
#    return plus_method.invoke_method(args.items, suppress_default=True)
#
#plus_method.default = BuiltinFunction(plus_default)
#
#@plus_method.register(Integer, Integer)
#def plus_int_int(argv):
#    arg0 = argv[0]
#    arg1 = argv[1]
#    assert isinstance(arg0, Integer)
#    assert isinstance(arg1, Integer)
#    return Integer(arg0.value + arg1.value)
#
##binary_arithmetic('+', lambda a, b: a + b)
#
#binary_arithmetic('-', lambda a, b: a - b)
#binary_arithmetic('*', lambda a, b: a * b)
#binary_arithmetic('/', lambda a, b: a / b)
#binary_arithmetic('%', lambda a, b: a % b)
#binary_arithmetic('|', lambda a, b: a | b)
#binary_arithmetic('&', lambda a, b: a & b)
#binary_arithmetic('^', lambda a, b: a ^ b)
#binary_arithmetic('<<', lambda a, b: a << b)
#binary_arithmetic('>>', lambda a, b: a >> b)
#binary_arithmetic('min', lambda a, b: min(a,b))
#binary_arithmetic('max', lambda a, b: max(a,b))
#
#
#binary_comparison('<', lambda a, b: a < b)
#binary_comparison('>', lambda a, b: a > b)
#binary_comparison('<=', lambda a, b: a <= b)
#binary_comparison('>=', lambda a, b: a >= b)
