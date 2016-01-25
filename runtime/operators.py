from space import *

clamp = Multimethod(3)
coerce = Multimethod(2)
concat = Multimethod(2)
neg = Multimethod(1)
pos = Multimethod(1)
ne  = Multimethod(2)
eq  = Multimethod(2)

by_symbol = {
    u'clamp': clamp,
    u'coerce': coerce,
    u'++': concat,
    u'!=': ne,
    u'==': eq,
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

# Not actual implementations of these functions
# All of these will be multimethods
@signature(Integer, Integer)
def cmp_lt(a, b):
    return boolean(a.value < b.value)

@signature(Integer, Integer)
def cmp_gt(a, b):
    return boolean(a.value > b.value)

@signature(Integer, Integer)
def cmp_le(a, b):
    return boolean(a.value <= b.value)

@signature(Integer, Integer)
def cmp_ge(a, b):
    return boolean(a.value >= b.value)

# TODO: turn into multimethods
by_symbol[u'<']  = Builtin(cmp_lt, u'<')
by_symbol[u'>']  = Builtin(cmp_gt, u'>')
by_symbol[u'<='] = Builtin(cmp_le, u'<=')
by_symbol[u'>='] = Builtin(cmp_ge, u'>=')

@signature(Object, Object)
def ne_default(a, b):
    return boolean(a != b)
ne.default = Builtin(ne_default)

@ne.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value != b.value)

@ne.multimethod_s(String, String)
def _(a, b):
    return boolean(not a.eq(b))

@signature(Object, Object)
def eq_default(a, b):
    return boolean(a == b)
eq.default = Builtin(eq_default)

@eq.multimethod_s(Integer, Integer)
def _(a, b):
    return boolean(a.value == b.value)

@eq.multimethod_s(String, String)
def _(a, b):
    return boolean(a.eq(b))

@neg.multimethod_s(Integer)
def _(a):
    return Integer(-a.value)

@pos.multimethod_s(Integer)
def _(a):
    return Integer(+a.value)

@concat.multimethod_s(String, String)
def _(a, b):
    return String(a.string + b.string)
@concat.multimethod_s(List, List)
def _(a, b):
    return List(a.contents + b.contents)

