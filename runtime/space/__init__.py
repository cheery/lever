from rpython.rlib.objectmodel import specialize, always_inline
from interface import Object, Interface, null, cast, cast_for
from builtin import Builtin, signature, expectations_error
from dictionary import Dict
from listobject import List
from module import Module
from multimethod import Multimethod
from numbers import Float, Integer, Boolean, to_float, to_int, true, false, is_true, is_false, boolean
from string import String
from uint8array import Uint8Array, to_uint8array
from exnihilo import Exnihilo
from customobject import CustomObject, Property
from rpython.rlib import jit
from setobject import Set
from errors import *
import operators

def as_cstring(value):
    if isinstance(value, String):
        return value.string.encode('utf-8')
    raise OldError(u"expected string and got " + value.repr())

def from_cstring(value):
    assert isinstance(value, str)
    return String(value.decode('utf-8'))

def from_ustring(value):
    assert isinstance(value, unicode)
    return String(value)

@always_inline
def get_interface(obj):
    if isinstance(obj, CustomObject):
        return obj.custom_interface
    return obj.__class__.interface
