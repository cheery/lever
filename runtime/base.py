from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rstring import UnicodeBuilder
from space import *
from evaluator.loader import from_object, SourceLocation
from evaluator.sourcemaps import TraceEntry
from async_io import Event, Queue
import core
import os
import pathobj
#import stdlib
import sys
import time
import vectormath
import uv_handle
import uv_stream

# The base environment
module = Module(u'base', {
    u'builtin': Builtin.interface,
    u'greenlet': core.Greenlet.interface,
    u'interface': Interface.interface,
    u'dict': Dict.interface,
    u'module': Module.interface,
    u'exnihilo': Exnihilo.interface,
    u'object': Object.interface,
    u'list': List.interface,
    u'multimethod': Multimethod.interface,
    u'float': Float.interface,
    u'int': Integer.interface,
    u'bool': Boolean.interface,
    u'str': String.interface,
    u'null': null,
    u'true': true,
    u'false': false,
    u'path': pathobj.Path.interface,
    u'property': Property.interface,
    u'Uint8Array': Uint8Array.interface,
    u'Uint8Slice': Uint8Slice.interface,
    u'Uint8Builder': Uint8Builder.interface,
    u'Utf8Decoder': Utf8Decoder.interface,
    u'StringBuilder': StringBuilder_.interface,
    u'schedule': Builtin(core.schedule, u'schedule'),
    u'set': Set.interface,
    u'slice': Slice.interface,
    u'SourceLocationLines': SourceLocationLines.interface,
    u'SourceLocation': SourceLocation.interface,
    u'DocRef': DocRef.interface,
    u'Event': Event.interface,
    u'Queue': Queue.interface,
    u'Handle': uv_handle.Handle.interface,
    u'Stream': uv_stream.Stream.interface,
    u'TTY': uv_stream.TTY.interface,
    u'Pipe': uv_stream.Pipe.interface,
}, frozen=True)

@Module.instantiator
@signature(String, Module, optional=1)
def module_instantiate(name, extends):
    return Module(name.string, {}, extends)

# we may later want to do the same for the stuff you see above.
for error in all_errors:
    module.setattr_force(error.interface.name, error.interface)

for name, value in operators.by_symbol.iteritems():
    module.setattr_force(name, value)

for name, value in vectormath.by_symbol.iteritems():
    module.setattr_force(name, value)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

@builtin
@signature(Object, Object, optional=1)
def load(program, path):
    if path is None:
        path = null
    else:
        path = pathobj.to_path(path)
    return from_object(program, path)

@builtin
def class_(argv):
    exnihilo = argv[0]
    parent = Object.interface
    name = String(u"customobject")
    assert 1 <= len(argv) <= 3
    if len(argv) > 1:
        parent = argv[1]
    if len(argv) > 2:
        name = argv[2]
    assert isinstance(exnihilo, Exnihilo)
    assert isinstance(parent, Interface)
    assert isinstance(name, String)
    interface = Interface(parent, name.string)
    interface.methods = {}
    for name, index in exnihilo.map.attribute_indexes.items():
        interface.methods[name] = exnihilo.storage[index]
    interface.instantiate = CustomObject.interface.instantiate
    return interface

@builtin
@signature(Object)
def iter_(obj):
    return obj.iter()

@builtin
@signature(Object)
def hash_(obj):
    return Integer(obj.hash())

@builtin
@signature(Object)
def repr_(obj):
    return String(obj.repr())

@builtin
@signature(List)
def reversed_(obj):
    return ReversedListIterator(reversed(obj.contents))

class ReversedListIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

    def iter(self):
        return self

@ReversedListIterator.method(u"next", signature(ReversedListIterator))
def ReversedListIterator_next(self):
    return self.iterator.next()
  
@builtin
@signature(Object, Object)
def getitem(obj, index):
    return obj.getitem(index)

@builtin
@signature(Object, Object, Object)
def setitem(obj, index, value):
    return obj.setitem(index, value)

@builtin
@signature(Object)
def listattr(obj):
    return List(obj.listattr())

@builtin
@signature(Object, String)
def getattr(obj, index):
    return obj.getattr(index.string)

@builtin
@signature(Object, String, Object)
def setattr(obj, index, value):
    return obj.setattr(index.string, value)

@builtin
@signature(String)
def ord_(string):
    if len(string.string) != 1:
        raise unwind(LError(u"ord expects a char"))
    return Integer(ord(string.string[0]))

@builtin
@signature(Integer)
def chr_(value):
    return String(unichr(value.value))

@builtin
@signature(Object, Object)
def isinstance_(value, which_list):
    if isinstance(which_list, List):
        whichs = which_list.contents
    else:
        whichs = [which_list]
    interface = get_interface(value)
    while interface is not null:
        if interface in whichs:
            return true
        # There should be exactly one recursively defined interface.
        if interface.parent is interface:
            return false
        interface = interface.parent
    return false
  
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
def len_(obj):
    return obj.getattr(u'length')

@builtin
@signature(Object)
def not_(a):
    return boolean(is_false(a))

@builtin
@signature(String)
def encode_utf8(value):
    return to_uint8array(value.string.encode('utf-8'))

@builtin
@signature(Uint8Data)
def decode_utf8(value):
    s = rffi.charp2str(rffi.cast(rffi.CCHARP, value.uint8data))
    return String(s.decode('utf-8'))

@builtin
def time_(argv):
    return Float(time.time())

@builtin
@signature()
def getcwd():
    return pathobj.getcwd()

@builtin
@signature(Object)
def chdir(obj):
    pathobj.chdir(obj)
    return null

@builtin
@signature(Integer, Integer, Integer, optional=2)
def range_(start, stop, step):
    if stop is None:
        stop  = start.value
        start = 0
    else:
        start = start.value
        stop  = stop.value
    if step is None:
        step = 1
    else:
        step = step.value
    if step == 0:
        raise unwind(LTypeError(u"step==0"))
    return Range(start, stop, step)

class Range(Object):
    __slots__ = ['start', 'stop', 'step', 'sign', 'current']
    _immutable_fields_ = ['start', 'stop', 'step', 'sign']
    def __init__(self, start, stop, step):
        self.current = start
        self.stop = stop
        self.step = step
        self.sign = +1 if step >= 0 else -1

    def iter(self):
        return self

@Range.method(u"next", signature(Range))
def Range_next(self):
    if self.current*self.sign < self.stop*self.sign:
        i = self.current
        self.current += self.step
        return Integer(i)
    raise StopIteration()

# These two functions are used by the lever compiler, so changing
# them will change the language. Take care..
@builtin
@signature(String, Integer, optional=1)
def parse_int(string, base):
    base = 10 if base is None else base.value
    value = 0
    for ch in string.string:
        if u'0' <= ch and ch <= u'9':
            digit = ord(ch) - ord('0')
        elif u'a' <= ch and ch <= u'z':
            digit = ord(ch) - ord('a') + 10
        elif u'A' <= ch and ch <= u'Z':
            digit = ord(ch) - ord('A') + 10
        else:
            raise unwind(LError(u"invalid digit char: " + ch))
        value = value * base + digit
    return Integer(value)

import math
# This needs to be extended. I would prefer partial or whole C-compatibility.
@builtin
@signature(String)
def parse_float(string):
    value = 0.0
    inv_scale = 1
    divider = 1
    exponent = 0.0
    exponent_sign = +1.0
    mode = 0
    for ch in string.string:
        if mode == 0:
            if u'0' <= ch and ch <= u'9':
                digit = ord(ch) - ord(u'0')
                value = value * 10.0 + digit
                inv_scale *= divider
            elif u'.' == ch:
                divider = 10
            elif u'e' == ch or u'E' == ch:
                mode = 1
            else:
                raise unwind(LError(u"invalid digit char: " + ch))
        elif mode == 1:
            mode = 2
            if u'+' == ch:
                exponent_sign = +1.0
                continue
            if u'-' == ch:
                exponent_sign = -1.0
                continue
        else: # mode == 2
            if u'0' <= ch and ch <= u'9':
                digit = ord(ch) - ord(u'0')
                exponent = exponent * 10.0 + digit
            else:
                raise unwind(LError(u"invalid digit char: " + ch))
    exponent = exponent_sign * exponent
    return Float((value / inv_scale) * math.pow(10.0, exponent))

@builtin
@signature(Interface)
def super_(interface):
    return interface.parent

#@builtin
#@signature(Object)
#def attach_debugger(debugger):
#    ec = main.get_ec()
#    ec.debug_hook = debugger
#    return null

import rlibuv as uv
@builtin
@signature(space.Integer, optional=1)
def exit(obj):
    ec = core.get_ec()
    ec.exit_status = 0 if obj is None else int(obj.value)
    uv.stop(ec.uv_loop)
    ec.enqueue(ec.current)        # Trick to ensure we get Discard -exception here
    return core.switch([ec.eventloop]) # Once they are created.

@builtin
@signature()
def getcurrent():
    return core.get_ec().current

@builtin
@signature()
def new_log():
    queue = Queue()
    ec = core.get_ec()
    if queue in ec.loggers:
        raise unwind(LError(u"queue has been registered twice."))
    ec.loggers.append(queue)
    return queue
 
@builtin
def print_(argv):
    ec = core.get_ec()
    ec.log_other(u"info", List(argv))
    return null

@builtin
@signature(String, Object)
def log(type, value):
    ec = core.get_ec()
    ec.log_other(type.string, value)
    return null

@builtin
@signature(Object)
def print_traceback(exception):
    ec = core.get_ec()
    ec.log_exception(exception)
    return null

@builtin
@signature(Object)
def format_traceback(exception):
    return String(format_traceback_raw(exception))

def format_traceback_raw(exception):
    traceback = exception.getattr(u"traceback")
    if not isinstance(traceback, space.List):
        raise space.unwind(space.LError(u"Expected null or list as .traceback: %s" % traceback.repr()))
    out = u""
    if len(traceback.contents) > 0:
        out = u"\033[31mTraceback:\033[36m\n"
    for entry in reversed(traceback.contents):
        if not isinstance(entry, TraceEntry):
            continue
        name, col0, lno0, col1, lno1 = entry.pc_location()
        out += u"    %s: %d,%d : %d,%d\n" % (name.repr(), lno0, col0, lno1, col1)
    out += u"\033[31m"
    out += space.get_interface(exception).name
    out += u":\033[0m"
    return out + u" " + exception.repr()

