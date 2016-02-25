from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rtyper.lltypesystem import rffi
from space import *
import main
import module_resolution
import operators
import os
import pathobj
#import stdlib
import sys
import time
import vectormath

# The base environment
module = Module(u'base', {
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
}, frozen=True)

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
    interface.methods = exnihilo.cells
    interface.instantiate = CustomObject.interface.instantiate
    return interface

@builtin
@signature(Object)
def interface(obj):
    return get_interface(obj)

@builtin
@signature(Object)
def iter_(obj):
    return obj.iter()

@builtin
@signature(Object)
def repr_(obj):
    return String(obj.repr())
  
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
    assert len(string.string) == 1
    return Integer(ord(string.string[0]))

@builtin
@signature(Integer)
def chr_(value):
    return String(unichr(value.value))

@builtin
@signature(Object, Object)
def isinstance_(value, which):
    interface = get_interface(value)
    while interface is not null:
        if interface is which:
            return true
        # There should be exactly one recursively defined interface.
        if interface.parent is interface:
            return false
        interface = interface.parent
    return true
 
#def pyl_callattr(argv):
#    assert len(argv) >= 2
#    name = argv[1]
#    assert isinstance(name, String)
#    return argv[0].callattr(name.string, argv[2:len(argv)])

@builtin
def print_(argv):
    space = u''
    out = u""
    for arg in argv:
        if isinstance(arg, String):
            string = arg.string
        else:
            string = arg.repr()
        out += space + string
        space = u' '
    os.write(1, (out + u'\n').encode('utf-8'))
    return null
  
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

@builtin
@signature(String)
def encode_utf8(value):
    return to_uint8array(value.string.encode('utf-8'))

@builtin
@signature(Uint8Array)
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
@signature(Integer, optional=1)
def exit(obj):
    status = 0 if obj is None else obj.value
    raise unwind(SystemExitObject(status))
