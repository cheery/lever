from rpython.rlib.rfloat import (
    DTSF_ADD_DOT_0, DTSF_STR_PRECISION, INFINITY, NAN, copysign,
    float_as_rbigint_ratio, formatd, isfinite, isinf, isnan)
from interface import Object, null, cast_for
from rpython.rlib.objectmodel import compute_hash
from builtin import signature
import math
import space

class Float(Object):
    _immutable_fields_ = ['number']
    __slots__ = ['number']
    __attrs__ = ['number']
    def __init__(self, number):
        self.number = number

    def repr(self):
        return float_to_string(self.number)

    def hash(self):
        return compute_hash(self.number)

    def eq(self, other):
        if isinstance(other, Float):
            return self.number == other.number
        return False

# There is potentially a lot more to consider on generic case of
# stringifying floats, but we get ahead with this for a while.
@Float.method(u"to_string", signature(Float))
def Float_to_string(self):
    return space.String(float_to_string(self.number))

def float_to_string(x, code='g', precision=DTSF_STR_PRECISION):
    if isfinite(x):
        s = formatd(x, code, precision, DTSF_ADD_DOT_0)
    elif isinf(x):
        if x > 0.0:
            s = "inf"
        else:
            s = "-inf"
    else:  # isnan(x):
        s = "nan"
    return s.decode('utf-8')

class Integer(Object):
    _immutable_fields_ = ['value']
    __slots__ = ['value']
    __attrs__ = ['value']
    def __init__(self, value):
        self.value = value

    def repr(self):
        return u"%d" % self.value

    def hash(self):
        return compute_hash(int(self.value))

    def eq(self, other):
        if isinstance(other, Integer):
            return self.value == other.value
        return False
Integer.interface.name = u"int"

# We are not doing implicit conversion of strings to numbers.
# although this method is named similarly as the one in javascript.
@Integer.method(u"to_string", signature(Integer, Integer, optional=1))
def Integer_to_string(integer, base):
    base = 10 if base is None else base.value
    if base >= len(digits):
        raise space.unwind(space.LError(u"not enough digits to represent this base %d" % base))
    if base < 0:
        raise space.unwind(space.LError(u"negative base not supported"))
    return space.String(integer_to_string(integer.value, base))

def integer_to_string(integer, base):
    if integer < 0:
        integer = -integer
        sign = u"-"
    else:
        integer = integer
        sign = u""
    out = []
    while integer > 0:
        out.append(digits[integer % base])
        integer /= base
    out.reverse()
    if len(out) == 0:
        return u"0"
    return sign + u"".join(out)

digits = "0123456789abcdefghijklmnopqrstuvwxyz"

class Boolean(Object):
    _immutable_fields_ = ['flag']
    __slots__ = ['flag']
    __attrs__ = ['flag']
    def __init__(self, flag):
        self.flag = flag

    def hash(self):
        return 1 if self.flag else 0

    def eq(self, other):
        if isinstance(other, Boolean):
            return self.flag == other.flag
        return False

    def repr(self):
        if self.flag:
            return u"true"
        else:
            return u"false"

def to_float(obj):
    if isinstance(obj, Float):
        return obj.number
    elif isinstance(obj, Integer):
        return float(obj.value)
    elif isinstance(obj, Boolean):
        if is_true(obj):
            return 1.0
        else:
            return 0.0
    else:
        raise space.unwind(space.LTypeError(u"expected float value"))

def to_int(obj):
    if isinstance(obj, Float):
        return int(obj.number)
    elif isinstance(obj, Integer):
        return obj.value
    elif isinstance(obj, Boolean):
        if is_true(obj):
            return 1
        else:
            return 0
    else:
        raise space.unwind(space.LTypeError(u"expected int value"))

true = Boolean(True)
false = Boolean(False)

def is_true(flag):
    return flag is not null and flag is not false and flag is not None

def is_false(flag):
    return flag is null or flag is false or flag is None

def boolean(cond):
    return true if cond else false

@Float.instantiator
@signature(Object)
@cast_for(Float)
def instantiate(obj):
    return Float(to_float(obj))

@Integer.instantiator
@signature(Object)
@cast_for(Integer)
def instantiate(obj):
    return Integer(to_int(obj))

@Boolean.instantiator
@signature(Object)
@cast_for(Boolean)
def instantiate(obj):
    return boolean(is_true(obj))


## Representational values

# Aaron Meurer, lead developer of Sympy, proposed that
# it would be useful to be able of recover the float number as user typed it.

# I made this subtypes for floats, the idea is that if you
# convert this to a string before you do arithmetic on them, you're going to
# recover the number representation like the user typed it.

class FloatRepr(Float):
    def __init__(self, string):
        Float.__init__(self, parse_float_(string))
        self.string = string

@FloatRepr.method(u"to_string", signature(FloatRepr))
def FloatRepr_to_string(self):
    return self.string

# These two functions are used by the lever compiler, so changing
# them will change the language. Take care..
def parse_int_(string, base):
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
            raise space.unwind(space.LError(u"invalid digit char: " + ch))
        if digit >= base:
            raise space.unwind(space.LError(u"invalid digit char: " + ch))
        value = value * base + digit
    return value

# This needs to be extended. I would prefer partial or whole C-compatibility.
def parse_float_(string):
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
                raise space.unwind(space.LError(u"invalid digit char: " + ch))
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
                raise space.unwind(space.LError(u"invalid digit char: " + ch))
    exponent = exponent_sign * exponent
    return (value / inv_scale) * math.pow(10.0, exponent)
