# We may want to invert many of these dependencies.
from builtin import Builtin, signature, expectations_error
from interface import Object, Interface, null
from multimethod import Multimethod
from numbers import Float, Integer, Boolean, to_float, to_int, true, false, is_true, is_false, boolean
from rpython.rlib.objectmodel import specialize, always_inline
from string import String
from listobject import List
from setobject import Set
from slices import Slice
import setobject
import space

clamp = Multimethod(3)
coerce = Multimethod(2)
concat = Multimethod(2)
neg = Multimethod(1)
pos = Multimethod(1)
ne  = Multimethod(2)
eq  = Multimethod(2)
lt  = Multimethod(2)
le  = Multimethod(2)
gt  = Multimethod(2)
ge  = Multimethod(2)

by_symbol = {
    u'clamp': clamp,
    u'coerce': coerce,
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
        assert isinstance(args, List)
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
shl  = arithmetic_multimethod(u'<<',  (lambda a, b: a << b))
shr  = arithmetic_multimethod(u'>>',  (lambda a, b: a >> b))
min_ = arithmetic_multimethod(u'min', (lambda a, b: min(a, b)), flo=True)
max_ = arithmetic_multimethod(u'max', (lambda a, b: max(a, b)), flo=True)

# You get a float if you divide.
div  = by_symbol[u'/'] = Multimethod(2)
coerce_by_default(div)

@div.multimethod_s(Integer, Integer)
def _(a, b):
    return Float(float(a.value) / float(b.value))

@div.multimethod_s(Float, Float)
def _(a, b):
    return Float(a.number / b.number)

# Binary coercion is used in lever arithmetic to turn left and right side into
# items that can be calculated with.
@coerce.multimethod_s(Boolean, Boolean)
def _(a, b):
    return List([Integer(int(a.flag)), Integer(int(b.flag))])

@coerce.multimethod_s(Integer, Boolean)
def _(a, b):
    return List([a, Integer(int(b.flag))])

@coerce.multimethod_s(Boolean, Integer)
def _(a, b):
    return List([Integer(int(a.flag)), b])

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

@signature(Object, Object)
def eq_default(a, b):
    return boolean(a == b)
eq.default = Builtin(eq_default)

@eq.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value == b.value)

@eq.multimethod_s(Float, Float)
def _(a, b):
    return boolean(a.number == b.number)

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
