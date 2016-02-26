from interface import Object, null
import space
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
        return Object.setattr(self, name, value)

class LError(LException):
    def __init__(self, message):
        self.message = message
        self.traceback = null

    def repr(self):
        return self.message

class LAssertionError(LException):
    def __init__(self, thing):
        self.thing = thing
        self.traceback = null

    def repr(self):
        return self.thing.repr()

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

class LKeyError(LException):
    def __init__(self, obj, key):
        self.traceback = null
        self.obj = obj
        self.key = key

    def repr(self):
        return u"%s[%s]" % (self.obj.repr(), self.key.repr())

class LTypeError(LException):
    def __init__(self, message):
        self.message = message

    def repr(self):
        return self.message

class LFrozenError(LException):
    def __init__(self, obj):
        self.obj = obj

    def repr(self):
        return u"%s is frozen" % self.obj.repr()

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
    LTypeError,
    LFrozenError,
    LCallError,
    LInstructionError,
]
