# We may want to invert many of these dependencies.
from builtin import Builtin, signature
from interface import Object, Interface, null, cast
from customobject import Id
from multimethod import Multimethod
from numbers import Float, Integer, Boolean, to_float, to_int, true, false, is_true, is_false, boolean
from rpython.rlib.rarithmetic import LONG_BIT, ovfcheck
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rlib.rfloat import copysign
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem.module.ll_math import math_fmod
from string import String
from listobject import List
from setobject import Set
from slices import Slice
from uint8array import Uint8Array, Uint8Slice, Uint8Data, alloc_uint8array
import setobject
import space
import math

clamp = Multimethod(3)
coerce = Multimethod(2)
concat = Multimethod(2)
neg = Multimethod(1)
pos = Multimethod(1)
cmp_= Multimethod(2)
ne  = Multimethod(2)
eq  = Multimethod(2)
lt  = Multimethod(2)
le  = Multimethod(2)
gt  = Multimethod(2)
ge  = Multimethod(2)

by_symbol = {
    u'clamp': clamp,
    u'coerce': coerce,
    u'cmp': cmp_,
    u'++': concat,
    u'!=': ne,
    u'==': eq,
    u'<':  lt,
    u'>':  gt,
    u'<=': le,
    u'>=': ge,
    u'-expr': neg,
    u'+expr': pos,
}

def coerce_by_default(method):
    def default(argv):
        args = coerce.call(argv)
        if not isinstance(args, List):
            raise space.unwind(space.LError(u"coerce should return list"))
        return method.call_suppressed(args.contents)
    method.default = Builtin(default)

def arithmetic_multimethod(sym, operation, flo=False):
    operation = specialize.argtype(0, 1)(operation)
    method = Multimethod(2)
    coerce_by_default(method)
    @method.multimethod_s(Integer, Integer)
    def _(a, b):
        return Integer(operation(a.value, b.value))
    if flo:
        @method.multimethod_s(Float, Float)
        def _(a, b):
            return Float(operation(a.number, b.number))
    by_symbol[sym] = method
    return method

add  = arithmetic_multimethod(u'+',   (lambda a, b: a + b), flo=True)
sub  = arithmetic_multimethod(u'-',   (lambda a, b: a - b), flo=True)
mul  = arithmetic_multimethod(u'*',   (lambda a, b: a * b), flo=True)
or_  = arithmetic_multimethod(u'|',   (lambda a, b: a | b))
mod  = arithmetic_multimethod(u'%',   (lambda a, b: a % b))
and_ = arithmetic_multimethod(u'&',   (lambda a, b: a & b))
xor  = arithmetic_multimethod(u'^',   (lambda a, b: a ^ b))
min_ = arithmetic_multimethod(u'min', (lambda a, b: min(a, b)), flo=True)
max_ = arithmetic_multimethod(u'max', (lambda a, b: max(a, b)), flo=True)
# min default and max default redefined below.

shl = by_symbol[u'<<'] = Multimethod(2)
coerce_by_default(shl)

shr = by_symbol[u'>>'] = Multimethod(2)
coerce_by_default(shr)

@shl.multimethod_s(Integer, Integer)
def int_shl(a, b):
    a_v = a.value
    b_v = b.value
    if b_v < LONG_BIT: # 0 <= b < LONG_BIT
        c = ovfcheck(a_v << b_v)
        return Integer(c)
    if b_v < 0:
        raise space.unwind(space.LError(u"negative shift count"))
    # b_v >= LONG_BIT
    if a_v == 0:
        return a
    raise OverflowError

@shr.multimethod_s(Integer, Integer)
def int_shr(a, b):
    a_v = a.value
    b_v = b.value
    if b_v >= LONG_BIT: # not (0 <= b < LONG_BIT)
        if b_v < 0:
            raise space.unwind(space.LError(u"negative shift count"))
        # b >= LONG_BIT
        if a_v == 0:
            return a
        a_v = -1 if a_v < 0 else 0
    else:
        a_v = a_v >> b_v
    return Integer(a_v)

@mod.multimethod_s(Float, Float)
def float_mod(a, b):
    y = b.number
    mod = math_fmod(a.number, y)     # Follows pypy implementation.
    if mod:                          # I'm not sure why remainder and denominator
        if (y < 0.0) != (mod < 0.0): # must have the same sign.
            mod += y
    else:
        mod = copysign(0.0, y) 
    return Float(mod)

# You get a float if you divide.
div  = by_symbol[u'/'] = Multimethod(2)
coerce_by_default(div)

@div.multimethod_s(Integer, Integer)
def _(a, b):
    return Float(float(a.value) / float(b.value))

@div.multimethod_s(Float, Float)
def _(a, b):
    return Float(a.number / b.number)

# Long-time due.
floordiv  = by_symbol[u'//'] = Multimethod(2)
coerce_by_default(floordiv)

@floordiv.multimethod_s(Integer, Integer)
def _(a, b):
    return Integer(a.value // b.value)

@floordiv.multimethod_s(Float, Float)
def _(a, b):
    return Float(math.floor(a.number / b.number))

# Binary coercion is used in lever arithmetic to turn left and right side into
# items that can be calculated with.
#@coerce.multimethod_s(Boolean, Boolean)
#def _(a, b):
#    return List([Integer(int(a.flag)), Integer(int(b.flag))])

# There is a discussion that this can actually result in
# hiding of errors and isn't a very nice feature in the retrospect.
# We may have to deprecate the implicit int-bool coercion.
# Lets deprecate them and see what we'll get!
#@coerce.multimethod_s(Integer, Boolean)
#def _(a, b):
#    return List([a, Integer(int(b.flag))])
#
#@coerce.multimethod_s(Boolean, Integer)
#def _(a, b):
#    return List([Integer(int(a.flag)), b])

@coerce.multimethod_s(Integer, Float)
def _(a, b):
    return List([Float(float(a.value)), b])

@coerce.multimethod_s(Float, Integer)
def _(a, b):
    return List([a, Float(float(b.value))])

@lt.multimethod_s(Integer, Integer)
def cmp_lt(a, b):
    return boolean(a.value < b.value)

@gt.multimethod_s(Integer, Integer)
def cmp_gt(a, b):
    return boolean(a.value > b.value)

@le.multimethod_s(Integer, Integer)
def cmp_le(a, b):
    return boolean(a.value <= b.value)

@ge.multimethod_s(Integer, Integer)
def cmp_ge(a, b):
    return boolean(a.value >= b.value)

@lt.multimethod_s(Float, Float)
def cmp_lt(a, b):
    return boolean(a.number < b.number)

@gt.multimethod_s(Float, Float)
def cmp_gt(a, b):
    return boolean(a.number > b.number)

@le.multimethod_s(Float, Float)
def cmp_le(a, b):
    return boolean(a.number <= b.number)

@ge.multimethod_s(Float, Float)
def cmp_ge(a, b):
    return boolean(a.number >= b.number)

@lt.multimethod_s(String, String)
def _(a, b):
    return boolean(a.string < b.string)

@gt.multimethod_s(String, String)
def _(a, b):
    return boolean(a.string > b.string)

@le.multimethod_s(String, String)
def _(a, b):
    return boolean(a.string <= b.string)

@ge.multimethod_s(String, String)
def _(a, b):
    return boolean(a.string >= b.string)

@signature(Object, Object)
def ne_default(a, b):
    return boolean(is_false(eq.call([a, b])))
ne.default = Builtin(ne_default)

@ne.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value != b.value)

@ne.multimethod_s(Float, Float)
def _(a, b):
    return boolean(a.number != b.number)

@ne.multimethod_s(String, String)
def _(a, b):
    return boolean(a.string != b.string)

# The equality here is a bit convoluted, but it should be good.
@signature(Object, Object)
def eq_default(a, b):
    # This strongly enforces the null and boolean identity.
    # You can't mess it up by multimethod introductions.
    if a == null or b == null:
        return boolean(a == b)
    elif isinstance(a, Boolean) or isinstance(b, Boolean):
        return boolean(a == b)
    # This reflects how the cmp_ operates, with an exception that
    # if cmp cannot succeed, we will use the identity equality.
    args = [a,b]
    method = cmp_.fetch_method(args, True)
    if method is None:
        c = coerce.fetch_method(args, False)
        if c is not None:
            args = cast(c.call(args), List, u"coerce should return a list").contents
            method = cmp_.fetch_method(args, True)
    if method is not None:
        return boolean(
            cast(method.call(args),
                Integer, u"cmp should return an int").value == 0)
    else:
        # This way, the equality and inequality is always defined,
        # even if comparison is not defined for everything.
        return boolean(a == b)
eq.default = Builtin(eq_default)

@signature(Object, Object)
def lt_default(a, b):
    args = [a,b]
    method = cmp_.fetch_method(args, True)
    if method is not None:
        return boolean(
            cast(method.call(args),
                Integer, u"cmp should return an int").value < 0)
    else:
        args = cast(coerce.call(args), List,
            u"coerce should return a list")
        return lt.call_suppressed(args.contents)
lt.default = Builtin(lt_default)

@signature(Object, Object)
def le_default(a, b):
    args = [a,b]
    method = cmp_.fetch_method(args, True)
    if method is not None:
        return boolean(
            cast(method.call(args),
                Integer, u"cmp should return int").value <= 0)
    else:
        args = cast(coerce.call(args), List,
            u"coerce should return a list")
        return le.call_suppressed(args.contents)
le.default = Builtin(le_default)

@signature(Object, Object)
def gt_default(a, b):
    args = [a,b]
    method = cmp_.fetch_method(args, True)
    if method is not None:
        return boolean(
            cast(method.call(args),
                Integer, u"cmp should return int").value > 0)
    else:
        args = cast(coerce.call(args), List,
            u"coerce should return a list")
        return gt.call_suppressed(args.contents)
gt.default = Builtin(gt_default)

@signature(Object, Object)
def ge_default(a, b):
    args = [a,b]
    method = cmp_.fetch_method(args, True)
    if method is not None:
        return boolean(
            cast(method.call(args),
                Integer, u"cmp should return int").value >= 0)
    else:
        args = cast(coerce.call(args), List,
            u"coerce should return a list")
        return ge.call_suppressed(args.contents)
ge.default = Builtin(ge_default)

@signature(Object, Object)
def cmp_default(a, b):
    args = cast(coerce.call([a,b]), List,
        u"coerce should return a list")
    return cmp_.call_suppressed(args.contents)
cmp_.default = Builtin(cmp_default)

@eq.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value == b.value)

@eq.multimethod_s(Float, Float)
def _(a, b):
    return boolean(a.number == b.number)

@eq.multimethod_s(Integer, Float) # Added so they won't bite into back soon.
def _(a, b):
    return boolean(a.value == b.number)

@eq.multimethod_s(Float, Integer)
def _(a, b):
    return boolean(a.number == b.value)

@eq.multimethod_s(String, String)
def _(a, b):
    return boolean(a.string == b.string)

@eq.multimethod_s(List, List)
def _(a, b):
    if len(a.contents) != len(b.contents):
        return false
    for i in range(0, len(a.contents)):
        if is_false(eq.call([a.contents[i], b.contents[i]])):
            return false
    return true

@eq.multimethod_s(Id, Id)
def _(a, b):
    return boolean(a.ref == b.ref)

@eq.multimethod_s(Slice, Slice)
def _(a, b):
    if is_false( eq.call([a.start, b.start]) ):
        return false
    if is_false( eq.call([a.stop, b.stop]) ):
        return false
    if is_false( eq.call([a.step, b.step]) ):
        return false
    return true

@neg.multimethod_s(Integer)
def _(a):
    return Integer(-a.value)

@pos.multimethod_s(Integer)
def _(a):
    return Integer(+a.value)

@neg.multimethod_s(Float)
def _(a):
    return Float(-a.number)

@pos.multimethod_s(Float)
def _(a):
    return Float(+a.number)

@concat.multimethod_s(String, String)
def _(a, b):
    return String(a.string + b.string)
@concat.multimethod_s(List, List)
def _(a, b):
    return List(a.contents + b.contents)

@concat.multimethod_s(Uint8Array, Uint8Array)
@concat.multimethod_s(Uint8Slice, Uint8Array)
@concat.multimethod_s(Uint8Array, Uint8Slice)
@concat.multimethod_s(Uint8Slice, Uint8Slice)
def _(a, b):
    c = alloc_uint8array(a.length + b.length)
    rffi.c_memcpy(
        rffi.cast(rffi.VOIDP, c.uint8data),
        rffi.cast(rffi.VOIDP, a.uint8data), a.length)
    rffi.c_memcpy(
        rffi.cast(rffi.VOIDP, rffi.ptradd(c.uint8data, a.length)),
        rffi.cast(rffi.VOIDP, b.uint8data), b.length)
    return c

@eq.multimethod_s(Set, Set)
def cmp_eq(a, b):
    return boolean(a.eq(b))

@lt.multimethod_s(Set, Set)
def cmp_lt(a, b):
    t = setobject.Set_is_superset(b, a)
    if space.is_true(t) and len(a._set) != len(b._set):
        return space.true
    return space.false

@gt.multimethod_s(Set, Set)
def cmp_gt(a, b):
    t = setobject.Set_is_superset(a, b)
    if space.is_true(t) and len(a._set) != len(b._set):
        return space.true
    return space.false

@le.multimethod_s(Set, Set)
def cmp_le(a, b):
    return setobject.Set_is_superset(b, a)

@ge.multimethod_s(Set, Set)
def cmp_ge(a, b):
    return setobject.Set_is_superset(a, b)

@or_.multimethod_s(Set, Set)
def _(a, b):
    return setobject.Set_union(a, [b])

@and_.multimethod_s(Set, Set)
def _(a, b):
    return setobject.Set_intersection(a, [b])

@sub.multimethod_s(Set, Set)
def _(a, b):
    return setobject.Set_difference(a, [b])

@xor.multimethod_s(Set, Set)
def _(a, b):
    return setobject.Set_symmetric_difference(a, b)

@clamp.multimethod_s(Slice, Integer, Integer)
def _(c, start, stop):
    start, stop, step = c.clamped(start.value, stop.value)
    return Slice(Integer(start), Integer(stop), Integer(step))

@mul.multimethod_s(Integer, String)
def _(c, a):
    return String(a.string * c.value)

@mul.multimethod_s(String, Integer)
def _(a, c):
    return String(a.string * c.value)

def min_default(argv):
    if len(argv) == 2 and argv[1] is null:
        return argv[0]
    if len(argv) == 2 and argv[0] is null:
        return argv[1]
    args = coerce.call(argv)
    if not isinstance(args, List):
        raise space.unwind(space.LError(u"coerce should return list"))
    return min_.call_suppressed(args.contents)
min_.default = Builtin(min_default)

def max_default(argv):
    if len(argv) == 2 and argv[1] is null:
        return argv[0]
    if len(argv) == 2 and argv[0] is null:
        return argv[1]
    args = coerce.call(argv)
    if not isinstance(args, List):
        raise space.unwind(space.LError(u"coerce should return list"))
    return max_.call_suppressed(args.contents)
max_.default = Builtin(max_default)
