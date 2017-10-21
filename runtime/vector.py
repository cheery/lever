from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib import jit
from space import *
from rpython.rlib.rarithmetic import r_uint, r_ulonglong
import vectormath

class Vec(Object):
    def fetch(self, index):
        assert False, "abstract method"
        return null

    def get_length(self):
        assert False, "abstract method"
        return 0

    def match_length(self, other):
        L1 = self.get_length()
        L2 = other.get_length()
        if L1 != L2:
            raise OldError(u"vector size mismatch")
        return jit.promote(L1)

    def getattr(self, name):
        if name == u"x":
            return self.fetch(0)
        if name == u"y":
            return self.fetch(1)
        if name == u"z":
            return self.fetch(2)
        if name == u"w":
            return self.fetch(3)
        if 2 <= len(name) <= 4:
            return letter_swizzle(self, name)
        if name == u"length":
            return Integer(rffi.r_long(self.get_length()))
        return Object.getattr(self, name)

    def iter(self): # TODO: See if this has to be optimized.
        out = []
        for i in range(self.get_length()):
            out.append(self.fetch(i))
        return List(out).iter()

class FVec(Vec):
    interface = Vec.interface
    def fetch_f(self, index):
        assert False, "abstract method"
        return 0.0

    def fetch(self, index):
        return Float(self.fetch_f(index))

class FVec3(FVec):
    _immutable_fields_ = ['f0', 'f1', 'f2']
    interface = Vec.interface
    def __init__(self, f0, f1, f2):
        self.f0 = f0
        self.f1 = f1
        self.f2 = f2

    def fetch_f(self, index):
        if index == 0:
            return self.f0
        elif index == 1:
            return self.f1
        elif index == 2:
            return self.f2
        raise OldError(u"float vector access out of bounds")

    def get_length(self):
        return 3

class FVecN(FVec):
    _immutable_fields_ = ['f_scalars[*]']
    interface = Vec.interface
    def __init__(self, f_scalars):
        assert len(f_scalars) >= 2
        make_sure_not_resized(f_scalars)
        self.f_scalars = f_scalars

    def fetch_f(self, index):
        if index < len(self.f_scalars):
            return self.f_scalars[index]
        raise OldError(u"float vector access out of bounds")

    def get_length(self):
        return len(self.f_scalars)

class GVec(Vec):
    _immutable_fields_ = ['g_scalars[*]']
    interface = Vec.interface
    def __init__(self, g_scalars):
        assert len(g_scalars) >= 2
        make_sure_not_resized(g_scalars)
        self.g_scalars = g_scalars

    def fetch(self, index):
        if index < len(self.g_scalars):
            return self.g_scalars[index]
        raise OldError(u"generic vector access out of bounds")

    def get_length(self):
        return len(self.g_scalars)

@jit.unroll_safe
def compact(g_scalars, all_float):
    if all_float:
        f_scalars = [0.0] * len(g_scalars)
        for i, val in enumerate(g_scalars):
            f_scalars[i] = to_float(val)
        if len(f_scalars) == 3:
            return FVec3(f_scalars[0], f_scalars[1], f_scalars[2])
        return FVecN(f_scalars[:])
    return GVec(g_scalars[:])

@Vec.instantiator
@jit.unroll_safe
def Vec_init(argv):
    if len(argv) < 2:
        raise OldError(u"Too few arguments to vec()")
    all_float = True
    for arg in argv:
        if not isinstance(arg, Float):
            all_float = False
    return compact(argv, all_float)

@jit.unroll_safe
def letter_swizzle(self, name):
    name = jit.promote(name)
    result = [null] * len(name)
    for i, a in enumerate(name):
        if a == 'x':
            result[i] = self.fetch(0)
        elif a == 'y':
            result[i] = self.fetch(1)
        elif a == 'z':
            result[i] = self.fetch(2)
        elif a == 'w':
            result[i] = self.fetch(3)
        else:
            return Object.getattr(self, name)
    return compact(result, isinstance(self, FVec))

@operators.add.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_add(self, other):
    L = self.match_length(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) + other.fetch_f(i)
        if L == 3:
            return FVec3(f_result[0], f_result[1], f_result[2])
        return FVecN(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.add.call([self.fetch(i), other.fetch(i)])
    return GVec(result)

@operators.sub.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_sub(self, other):
    L = self.match_length(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) - other.fetch_f(i)
        if L == 3:
            return FVec3(f_result[0], f_result[1], f_result[2])
        return FVecN(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.sub.call([self.fetch(i), other.fetch(i)])
    return GVec(result)

@operators.mul.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_mul(self, other):
    L = self.match_length(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) * other.fetch_f(i)
        if L == 3:
            return FVec3(f_result[0], f_result[1], f_result[2])
        return FVecN(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.mul.call([self.fetch(i), other.fetch(i)])
    return GVec(result)

@operators.div.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_div(self, other):
    L = self.match_length(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) / other.fetch_f(i)
        if L == 3:
            return FVec3(f_result[0], f_result[1], f_result[2])
        return FVecN(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.div.call([self.fetch(i), other.fetch(i)])
    return GVec(result)

@vectormath.length.multimethod_s(Vec)
@jit.unroll_safe
def Vec_length(self):
    result = operators.mul.call([self.fetch(0), self.fetch(0)])
    for i in range(1, jit.promote(self.get_length())):
        result = operators.add.call([
            result,
            operators.mul.call([self.fetch(i), self.fetch(i)])
        ])
    return vectormath.sqrt_.call([result])

@vectormath.dot.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_dot(self, other):
    L = self.match_length(other)
    result = operators.mul.call([self.fetch(0), self.fetch(0)])
    for i in range(1, L):
        result = operators.add.call([
            result,
            operators.mul.call([self.fetch(i), other.fetch(i)])
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
