from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib import jit
from space import *
from rpython.rlib.rarithmetic import r_uint, r_ulonglong
import vectormath

class Vec(Object):
    _immutable_fields_ = ['scalars[*]']
    def __init__(self, scalars):
        assert len(scalars) >= 2
        make_sure_not_resized(scalars)
        self.scalars = scalars

    def getattr(self, name):
        if name == u"x":
            return self.scalars[0]
        if name == u"y":
            return self.scalars[1]
        if name == u"z":
            if len(self.scalars) < 3:
                raise OldError(u"getattr access out of bounds")
            return self.scalars[2]
        if name == u"w":
            if len(self.scalars) < 4:
                raise OldError(u"getattr access out of bounds")
            return self.scalars[3]
        if 2 <= len(name) <= 4:
            return letter_swizzle(self, name)
        if name == u"length":
            return Integer(rffi.r_long(len(self.scalars)))
        return Object.getattr(self, name)

    def iter(self): # TODO: See if this has to be optimized.
        return List(list(self.scalars)).iter()

@Vec.instantiator
def Vec_init(argv):
    if len(argv) < 2:
        raise OldError(u"Too few arguments to vec()")

    return Vec(argv[:])

@jit.unroll_safe
def letter_swizzle(self, name):
    name = jit.promote(name)
    result = [null] * len(name)
    for i, a in enumerate(name):
        if a == 'x':
            result[i] = self.scalars[0]
        elif a == 'y':
            result[i] = self.scalars[1]
        elif a == 'z':
            if len(self.scalars) < 3:
                raise OldError(u"swizzle access out of bounds")
            result[i] = self.scalars[2]
        elif a == 'w':
            if len(self.scalars) < 4:
                raise OldError(u"swizzle access out of bounds")
            result[i] = self.scalars[3]
        else:
            return Object.getattr(self, name)
    return Vec(result)

@jit.unroll_safe
@operators.add.multimethod_s(Vec, Vec)
def Vec_add(self, other):
    a = self.scalars
    b = other.scalars
    L = jit.promote(len(a))
    if L != len(b):
        raise OldError(u"Vector size mismatch")
    result = [null] * L
    for i in range(L):
        result[i] = operators.add.call([a[i], b[i]])
    return Vec(result)

@jit.unroll_safe
@operators.sub.multimethod_s(Vec, Vec)
def Vec_sub(self, other):
    a = self.scalars
    b = other.scalars
    L = jit.promote(len(a))
    if L != len(b):
        raise OldError(u"Vector size mismatch")
    result = [null] * L
    for i in range(L):
        result[i] = operators.sub.call([a[i], b[i]])
    return Vec(result)

@jit.unroll_safe
@operators.mul.multimethod_s(Vec, Vec)
def Vec_mul(self, other):
    a = self.scalars
    b = other.scalars
    L = jit.promote(len(a))
    if L != len(b):
        raise OldError(u"Vector size mismatch")
    result = [null] * L
    for i in range(L):
        result[i] = operators.mul.call([a[i], b[i]])
    return Vec(result)

@jit.unroll_safe
@operators.div.multimethod_s(Vec, Vec)
def Vec_div(self, other):
    a = self.scalars
    b = other.scalars
    L = jit.promote(len(a))
    if L != len(b):
        raise OldError(u"Vector size mismatch")
    result = [null] * L
    for i in range(L):
        result[i] = operators.div.call([a[i], b[i]])
    return Vec(result)

@jit.unroll_safe
@vectormath.length.multimethod_s(Vec)
def Vec_length(self):
    a = self.scalars
    result = operators.mul.call([a[0], a[0]])
    for i in range(1, jit.promote(len(a))):
        result = operators.add.call([
            result,
            operators.mul.call([a[i], a[i]])
        ])
    return vectormath.sqrt_.call([result])

@jit.unroll_safe
@vectormath.dot.multimethod_s(Vec, Vec)
def Vec_dot(self, other):
    a = self.scalars
    b = self.scalars
    L = jit.promote(len(a))
    if L != len(b):
        raise OldError(u"Vector size mismatch")
    result = operators.mul.call([a[0], b[0]])
    for i in range(1, L):
        result = operators.add.call([
            result,
            operators.mul.call([a[i], b[i]])
        ])
    return result

# improve to include Int,Float X Vec
# improve to cross product (2D, 3D)
# improve to include normalize
# improve to include reflect, refract
# neg
# pos

# clamp with vec, float, float
#            vec, vec, vec
