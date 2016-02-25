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
class ExceptionObject(Object):
    def getattr(self, name):
        if name == u"traceback":
            return self.traceback
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"traceback":
            self.traceback = value
        return Object.setattr(self, name, value)
ExceptionObject.interface.name = u"Exception"

class Error(ExceptionObject):
    def __init__(self, message):
        self.message = message
        self.traceback = null

    def repr(self):
        return self.message
Error.interface.name = u"Error"

class AssertionErrorObject(ExceptionObject):
    def __init__(self, thing):
        self.thing = thing
        self.traceback = null

    def repr(self):
        return self.thing.repr()
AssertionErrorObject.interface.name = u"AssertionError"

class SystemExitObject(ExceptionObject):
    def __init__(self, status):
        self.status = status

    def repr(self):
        return u"%d" % self.status
SystemExitObject.interface.name = u"SystemExit"

class UncatchedStopIteration(ExceptionObject):
    def __init__(self):
        self.traceback = null

    def repr(self):
        return u""
UncatchedStopIteration.interface.name = u"UncatchedStopIteration"

# Legacy handling for errors.
def OldError(message):
    return unwind(Error(message))

# convenience function to produce a valid unwinder.
# Note that you don't want to pass user tracebacks with this thing.
def unwind(exc):
    exc.traceback = traceback = space.List([])
    return Unwinder(exc, traceback)

# This is used to plug them into base module
all_errors = [
    Error,
    AssertionErrorObject,
    SystemExitObject,
    UncatchedStopIteration,
]
