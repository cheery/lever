from builtin import signature
from interface import Object, null
from string import String
import space
import os
# To have custom exceptions, we resort to having an unwinder.
class Unwinder(Exception):
    _immutable_fields_ = ['exception', 'traceback']
    __slots__ = ['exception', 'traceback']
    __attrs__ = ['exception', 'traceback']
    def __init__(self, exception, traceback):
        self.exception = exception
        self.traceback = traceback

# The exceptions themselves must be able to hold traceback.
class LException(Object):
    def getattr(self, name):
        if name == u"traceback":
            return self.traceback
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"traceback":
            self.traceback = value
            return null
        return Object.setattr(self, name, value)

class LError(LException):
    def __init__(self, message):
        self.message = message
        self.traceback = null

    def getattr(self, name):
        if name == u"message":
            return space.String(self.message)
        return LException.getattr(self, name)

    def repr(self):
        return self.message

@LError.instantiator
@signature(String)
def _(message):
    return LError(message.string)

class LAssertionError(LException):
    def __init__(self, thing):
        self.thing = thing
        self.traceback = null

    def repr(self):
        return self.thing.repr()

@LAssertionError.instantiator
@signature(Object)
def _(thing):
    return LAssertionError(thing)

class LSystemExit(LException):
    def __init__(self, status):
        self.status = status

    def repr(self):
        return u"%d" % self.status

class LUncatchedStopIteration(LException):
    def __init__(self):
        self.traceback = null

    def repr(self):
        return u""

class LAttributeError(LException):
    def __init__(self, obj, name):
        self.traceback = null
        self.obj = obj
        self.name = name

    def repr(self):
        return u"%s.%s" % (self.obj.repr(), self.name)

@LAttributeError.instantiator
@signature(Object, String)
def _(obj, name):
    return LAttributeError(obj, name.string)

class LKeyError(LException):
    def __init__(self, obj, key):
        self.traceback = null
        self.obj = obj
        self.key = key

    def repr(self):
        return u"%s[%s]" % (self.obj.repr(), self.key.repr())

@LKeyError.instantiator
@signature(Object, String)
def _(obj, name):
    return LAttributeError(obj, name.string)

class LValueError(LException):
    def __init__(self, obj, value):
        self.traceback = null
        self.obj = obj
        self.value = value

    def repr(self):
        return u"%s in %s" % (self.value.repr(), self.obj.repr())

@LValueError.instantiator
@signature(Object, Object)
def _(obj, value):
    return LValueError(obj, value)

class LTypeError(LException):
    def __init__(self, message):
        self.message = message

    def repr(self):
        return self.message

@LTypeError.instantiator
@signature(String)
def _(message):
    return LTypeError(message.string)

class LFrozenError(LException):
    def __init__(self, obj):
        self.obj = obj

    def repr(self):
        return u"%s is frozen" % self.obj.repr()

@LFrozenError.instantiator
@signature(Object)
def _(obj):
    return LFrozenError(obj)

# TODO: improve this. :)
# Consider putting trace entries into Builtins, so
# that tracebacks present movement through builtin
# entries as well.
class LCallError(LException):
    def __init__(self, min, max, variadic, got):
        self.min = min
        self.max = max
        self.variadic = variadic
        self.got = got

    def repr(self):
        if self.got < self.min:
            return u"expected at least %d arguments, received %d" % (self.min, self.got)
        return u"expected maximum %d arguments, received %d" % (self.max, self.got)

class LInstructionError(LException):
    def __init__(self, name, opcode):
        self.name = name
        self.opcode = opcode

    def repr(self):
        return u"unexpected instruction: " + self.name

class LIOError(LException):
    def __init__(self, filename, errno):
        self.filename = filename
        self.errno = errno

    def repr(self):
        message = os.strerror(self.errno).decode('utf-8')
        return u"%s: %s" % (self.filename.repr(), message)

# Legacy handling for errors.
def OldError(message):
    return unwind(LError(message))

# convenience function to produce a valid unwinder.
# Note that you don't want to pass user tracebacks with this thing.
def unwind(exc):
    exc.traceback = traceback = space.List([])
    return Unwinder(exc, traceback)

# This is used to plug them into base module
all_errors = [
    LError,
    LException,
    LAssertionError,
    LSystemExit,
    LUncatchedStopIteration,
    LAttributeError,
    LKeyError,
    LValueError,
    LTypeError,
    LFrozenError,
    LCallError,
    LInstructionError,
    LIOError,
]
