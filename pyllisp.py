# On the way of phasing this file out of the repository.
import sys, os
from object import Error, Object, List, String, Symbol, Boolean, Integer, BuiltinFunction, Multimethod, true, false, null, is_false
from reader import WontParse, PartialParse, read_file, read_source
from rpython.config.translationoption import get_combined_translation_config
from rpython.rlib.rtimer import read_timestamp
from rpython.rlib.objectmodel import we_are_translated
from ast_closure import interpret, Closure, Environment
import ffi

config = get_combined_translation_config(translating=True)
#config.translation.continuation = True

if config.translation.continuation:
    from rpython.rlib.rstacklet import StackletThread

class GlobalState:
    stacklet = None
    current = None # The current greenlet

class Greenlet(Object):
    def __init__(self, handle, initialized, argv=None):
        self.handle = handle
        self.initialized = initialized
        self.argv = argv
        self.parent = process.current
        self.callee = None

    def switch(self, argv):
        if not self.initialized:
            self.argv += argv
            self.initialized = True
            self.callee = process.current
            process.current = self
            self.handle = process.stacklet.new(greenlet_init)
            callee = process.stacklet.switch(self.handle)
            process.current.callee.handle = callee
        else:
            if process.stacklet.is_empty_handle(self.handle):
                raise Exception("dead greenlet")
            self.argv = argv
            self.callee = process.current
            process.current = self
            callee = process.stacklet.switch(self.handle)
            process.current.callee.handle = callee
        if len(process.current.argv) == 0:
            retval = null
        else:
            retval = process.current.argv[0]
        process.current.argv = None
        return retval

    def getattr(self, name):
        if name == 'switch':
            return GreenletSwitch(self)
        if name == 'parent':
            return self.parent or null
        return Object.getattr(self, name)

    def repr(self):
        return "<greenlet " + str(self.handle) + ">"

class GreenletSwitch(Object):
    def __init__(self, greenlet):
        self.greenlet = greenlet

    def invoke(self, argv):
        return self.greenlet.switch(argv)

    def repr(self):
        return self.greenlet.repr() + ".switch"

def greenlet_init(head, arg):
    # fill greenlet's handle.
    callee = process.stacklet.switch(head)
    process.current.callee.handle = callee
    current = process.current

    func = current.argv.pop(0)
    retval = func.invoke(current.argv)

    parent = process.current.parent
    while process.stacklet.is_empty_handle(parent.handle):
        parent = parent.parent
    parent.argv = [retval]
    parent.callee = process.current
    process.current = parent
    return parent.handle

process = GlobalState()

def pyl_print(argv):
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

def pyl_apply(argv):
    N = len(argv) - 1
    assert N >= 1
    args = argv[1:N]
    varg = argv[N]
    assert isinstance(varg, List)
    return argv[0].invoke(args + varg.items)

def pyl_list(argv):
    return List(argv)

def pyl_getitem(argv):
    assert len(argv) == 2
    return argv[0].getitem(argv[1])

def pyl_setitem(argv):
    assert len(argv) == 3
    return argv[0].setitem(argv[1], argv[2])

def pyl_getattr(argv):
    assert len(argv) == 2
    name = argv[1]
    assert isinstance(name, String)
    return argv[0].getattr(name.string)

def pyl_setattr(argv):
    assert len(argv) == 3
    name = argv[1]
    assert isinstance(name, String)
    return argv[0].setattr(name.string, argv[2])

def pyl_callattr(argv):
    assert len(argv) >= 2
    name = argv[1]
    assert isinstance(name, String)
    return argv[0].callattr(name.string, argv[2:len(argv)])

def pyl_getcurrent(argv):
    return process.current

def pyl_greenlet(argv):
    return Greenlet(process.current.handle, False, argv)

global_scope = {
    "print": BuiltinFunction(pyl_print, "print"),
    "apply": BuiltinFunction(pyl_apply, "apply"),
    "list": BuiltinFunction(pyl_list, "list"),
    "[]": BuiltinFunction(pyl_getitem, "[]"),
    "[]=": BuiltinFunction(pyl_setitem, "[]="),
    "getattr": BuiltinFunction(pyl_getattr, "getattr"),
    "setattr": BuiltinFunction(pyl_setattr, "setattr"),
    "callattr": BuiltinFunction(pyl_callattr, "callattr"),
    "true": true,
    "false": false,
    "null": null,
    "ffi": ffi.module,
}

if config.translation.continuation:
    global_scope.update({
        "getcurrent": BuiltinFunction(pyl_getcurrent, "getcurrent"),
        "greenlet": BuiltinFunction(pyl_greenlet, "greenlet"),
    })

def global_builtin(name):
    def _impl(fn):
        global_scope[name] = BuiltinFunction(fn, name)
        return fn
    return _impl

@global_builtin('read-file')
def pyl_read_file(argv):
    assert len(argv) >= 1
    arg0 = argv.pop(0)
    assert isinstance(arg0, String)
    return read_file(arg0.string)

@global_builtin('!=')
def pyl_equals(argv):
    assert len(argv) == 2
    arg0 = argv[0]
    arg1 = argv[1]
    if isinstance(arg0, Integer) and isinstance(arg1, Integer):
        if arg0.value == arg1.value:
            return false
        return true
    if arg0 is arg1:
        return false
    else:
        return true

@global_builtin('==')
def pyl_equals(argv):
    assert len(argv) == 2
    arg0 = argv[0]
    arg1 = argv[1]
    if isinstance(arg0, Integer) and isinstance(arg1, Integer):
        if arg0.value == arg1.value:
            return true
        return false
    if arg0 is arg1:
        return true
    else:
        return false

@global_builtin('and')
def pyl_and(argv):
    assert len(argv) == 2
    arg0 = argv[0]
    arg1 = argv[1]
    if is_false(arg0) or is_false(arg1):
        return false
    else:
        return true

@global_builtin('or')
def pyl_or(argv):
    assert len(argv) == 2
    arg0 = argv[0]
    arg1 = argv[1]
    if is_false(arg0) and is_false(arg1):
        return false
    else:
        return true

@global_builtin('not')
def pyl_not(argv):
    assert len(argv) == 1
    arg0 = argv[0]
    if is_false(arg0):
        return true
    else:
        return false

def binary_arithmetic(name, op):
    def _impl_(argv):
        assert len(argv) == 2
        arg0 = argv[0]
        arg1 = argv[1]
        if isinstance(arg0, Integer) and isinstance(arg1, Integer):
            return Integer(op(arg0.value, arg1.value))
        raise Exception("cannot i" + name + " " + arg0.repr() + " and " + arg1.repr())
    global_builtin(name)(_impl_)

def binary_comparison(name, op):
    def _impl_(argv):
        assert len(argv) == 2
        arg0 = argv[0]
        arg1 = argv[1]
        if isinstance(arg0, Integer) and isinstance(arg1, Integer):
            if op(arg0.value, arg1.value):
                return true
            else:
                return false
        raise Exception("cannot i" + name + " " + arg0.repr() + " and " + arg1.repr())
    global_builtin(name)(_impl_)

global_scope['coerce'] = coerce_method = Multimethod(2, default=None)

@coerce_method.register(Boolean, Integer)
def coerce_bool_int(argv):
    if len(argv) != 2:
        raise Exception("expected exactly 2 arguments")
    arg0 = argv[0]
    arg1 = argv[1]
    assert isinstance(arg0, Boolean)
    assert isinstance(arg1, Integer)
    return List([Integer(int(arg0.flag)), arg1])

@coerce_method.register(Integer, Boolean)
def coerce_bool_int(argv):
    if len(argv) != 2:
        raise Exception("expected exactly 2 arguments")
    arg0 = argv[0]
    arg1 = argv[1]
    assert isinstance(arg0, Integer)
    assert isinstance(arg1, Boolean)
    return List([arg0, Integer(int(arg1.flag))])

global_scope['+'] = plus_method = Multimethod(2, default=None)

def plus_default(argv):
    args = coerce_method.invoke(argv)
    assert isinstance(args, List)
    return plus_method.invoke_method(args.items, suppress_default=True)

plus_method.default = BuiltinFunction(plus_default)

@plus_method.register(Integer, Integer)
def plus_int_int(argv):
    arg0 = argv[0]
    arg1 = argv[1]
    assert isinstance(arg0, Integer)
    assert isinstance(arg1, Integer)
    return Integer(arg0.value + arg1.value)

#binary_arithmetic('+', lambda a, b: a + b)

binary_arithmetic('-', lambda a, b: a - b)
binary_arithmetic('*', lambda a, b: a * b)
binary_arithmetic('/', lambda a, b: a / b)
binary_arithmetic('%', lambda a, b: a % b)
binary_arithmetic('|', lambda a, b: a | b)
binary_arithmetic('&', lambda a, b: a & b)
binary_arithmetic('^', lambda a, b: a ^ b)
binary_arithmetic('<<', lambda a, b: a << b)
binary_arithmetic('>>', lambda a, b: a >> b)
binary_arithmetic('min', lambda a, b: min(a,b))
binary_arithmetic('max', lambda a, b: max(a,b))


binary_comparison('<', lambda a, b: a < b)
binary_comparison('>', lambda a, b: a > b)
binary_comparison('<=', lambda a, b: a <= b)
binary_comparison('>=', lambda a, b: a >= b)

from greenlet import getcurrent, greenlet
class StackletThreadShim:
    def __init__(self, config):
        self.config = config
        self.null_handle = getcurrent()

    def get_null_handle(self):
        return self.null_handle

    def new(self, callback):
        g = greenlet(callback)
        return g.switch(getcurrent(), 0)

    def switch(self, handle):
        return handle.switch(getcurrent())

    def is_empty_handle(self, handle):
        return handle.dead

def entry_point(argv):
    if config.translation.continuation:
        if we_are_translated():
            process.stacklet = StackletThread(config)
        else:
            process.stacklet = StackletThreadShim(config)
        process.current = Greenlet(process.stacklet.get_null_handle(), True)

    env = Environment(None, global_scope)
    if len(argv) <= 1:
        prompt = "pyl> "
        os.write(1, prompt)
        source = os.read(0, 4096)
        while source != "":
            try:
                try:
                    lst = read_source(source)
                except PartialParse as exc:
                    os.write(1, " "*len(prompt))
                    source += os.read(0, 4096)
                else:
                    assert isinstance(lst, List)
                    for expr in lst:
                        retval = interpret(env, expr)
                        pyl_print([retval])
                    os.write(1, prompt)
                    source = os.read(0, 4096)
            except Error as exc:
                os.write(1, exc.__class__.__name__ + ": " + exc.message + "\n")
                os.write(1, prompt)
                source = os.read(0, 4096)
        if source == "":
            os.write(1, "\n")
    else:
        #now = read_timestamp()
        #print "[STAMP BEGIN] "
        lst = read_file(argv[1])
        assert isinstance(lst, List)
        for expr in lst:
            interpret(env, expr)
        #delta = read_timestamp() - now
        #print "[STAMP NOW] " + str(delta)
    return 0

def target(*args):
    return entry_point, None

if __name__=='__main__':
    sys.exit(entry_point(sys.argv))
