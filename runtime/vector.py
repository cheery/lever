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

    def get_item_type(self):
        assert False, "abstract method"
        return null

    def match_interface(self, other):
        i1 = self.get_item_type()
        i2 = other.get_item_type()
        if i1 is i2:
            return i1
        raise OldError(u"vector element type mismatch")

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

    def get_item_type(self):
        return Float.interface

class FVec2(FVec):
    _immutable_fields_ = ['f0', 'f1']
    interface = Vec.interface
    def __init__(self, f0, f1):
        self.f0 = f0
        self.f1 = f1

    def fetch_f(self, index):
        if index == 0:
            return self.f0
        elif index == 1:
            return self.f1
        raise OldError(u"float vector access out of bounds")

    def get_length(self):
        return 2

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

class FVec4(FVec):
    _immutable_fields_ = ['f0', 'f1', 'f2', 'f3']
    interface = Vec.interface
    def __init__(self, f0, f1, f2, f3):
        self.f0 = f0
        self.f1 = f1
        self.f2 = f2
        self.f3 = f3

    def fetch_f(self, index):
        if index == 0:
            return self.f0
        elif index == 1:
            return self.f1
        elif index == 2:
            return self.f2
        elif index == 3:
            return self.f3
        raise OldError(u"float vector access out of bounds")

    def get_length(self):
        return 4

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
    def __init__(self, g_scalars, item_type):
        assert len(g_scalars) >= 2
        make_sure_not_resized(g_scalars)
        self.g_scalars = g_scalars
        self.item_type = item_type

    def fetch(self, index):
        if index < len(self.g_scalars):
            return self.g_scalars[index]
        raise OldError(u"generic vector access out of bounds")

    def get_length(self):
        return len(self.g_scalars)

    def get_item_type(self):
        return self.item_type

@jit.unroll_safe
def compact(g_scalars):
    if isinstance(g_scalars[0], Float):
        f_scalars = [0.0] * len(g_scalars)
        for i, val in enumerate(g_scalars):
            f_scalars[i] = to_float(val)
        return compact_f(f_scalars)
    interface = get_interface(g_scalars[0])
    for scalar in g_scalars:
        if get_interface(scalar) != interface:
            raise OldError(u"every element in vector must have same interface")
    return GVec(g_scalars[:], interface)

def compact_f(f_scalars):
    if len(f_scalars) == 2:
        return FVec2(f_scalars[0], f_scalars[1])
    elif len(f_scalars) == 3:
        return FVec3(f_scalars[0], f_scalars[1], f_scalars[2])
    elif len(f_scalars) == 4:
        return FVec4(f_scalars[0], f_scalars[1], f_scalars[2], f_scalars[3])
    else:
        return FVecN(f_scalars[:])

@Vec.instantiator # TODO: put it to use instantiator.
@jit.unroll_safe
def Vec_init(argv):
    if len(argv) < 2:
        raise OldError(u"Too few arguments to vec()")
    return compact(argv)

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
    return compact(result)

@jit.unroll_safe
def Vec_arithmetic(self, s, op, lam):
    L = self.get_length()
    if isinstance(self, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = lam(self.fetch_f(i), s.number)
        return compact_f(f_result)
    result = [null] * L
    interface = get_interface(self)
    for i in range(L):
        result[i] = op.call([self.fetch(i), s])
    return GVec(result, interface)

@operators.add.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_add(self, other):
    L = self.match_length(other)
    interface = self.match_interface(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) + other.fetch_f(i)
        return compact_f(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.add.call([self.fetch(i), other.fetch(i)])
    return GVec(result, interface)

@operators.add.multimethod_s(Float, Vec)
@jit.unroll_safe
def Vec_add(s, self):
    return Vec_arithmetic(self, s, operators.add, lambda l, r: l + r)

@operators.add.multimethod_s(Vec, Float)
@jit.unroll_safe
def Vec_add(self, s):
    return Vec_arithmetic(self, s, operators.add, lambda l, r: l + r)

@operators.add.multimethod_s(Vec, Integer)
@jit.unroll_safe
def Vec_add(self, s):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l + r)

@operators.add.multimethod_s(Integer, Vec)
@jit.unroll_safe
def Vec_add(s, self):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l + r)

@operators.sub.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_sub(self, other):
    L = self.match_length(other)
    interface = self.match_interface(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) - other.fetch_f(i)
        return compact_f(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.sub.call([self.fetch(i), other.fetch(i)])
    return GVec(result, interface)

@operators.sub.multimethod_s(Float, Vec)
@jit.unroll_safe
def Vec_sub(s, self):
    return Vec_arithmetic(self, s, operators.sub, lambda l, r: l - r)

@operators.sub.multimethod_s(Vec, Float)
@jit.unroll_safe
def Vec_sub(self, s):
    return Vec_arithmetic(self, s, operators.sub, lambda l, r: l - r)

@operators.sub.multimethod_s(Vec, Integer)
@jit.unroll_safe
def Vec_add(self, s):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l - r)

@operators.sub.multimethod_s(Integer, Vec)
@jit.unroll_safe
def Vec_add(s, self):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l - r)

@operators.mul.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_mul(self, other):
    L = self.match_length(other)
    interface = self.match_interface(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) * other.fetch_f(i)
        return compact_f(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.mul.call([self.fetch(i), other.fetch(i)])
    return GVec(result, interface)

@operators.mul.multimethod_s(Float, Vec)
@jit.unroll_safe
def Vec_mul(s, self):
    return Vec_arithmetic(self, s, operators.mul, lambda l, r: l * r)

@operators.mul.multimethod_s(Vec, Float)
@jit.unroll_safe
def Vec_mul(self, s):
    return Vec_arithmetic(self, s, operators.mul, lambda l, r: l * r)

@operators.mul.multimethod_s(Vec, Integer)
@jit.unroll_safe
def Vec_add(self, s):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l * r)

@operators.mul.multimethod_s(Integer, Vec)
@jit.unroll_safe
def Vec_add(s, self):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l * r)

@operators.div.multimethod_s(Vec, Vec)
@jit.unroll_safe
def Vec_div(self, other):
    interface = self.match_interface(other)
    L = self.match_length(other)
    if isinstance(self, FVec) and isinstance(other, FVec):
        f_result = [0.0] * L
        for i in range(L):
            f_result[i] = self.fetch_f(i) / other.fetch_f(i)
        return compact_f(f_result)
    result = [null] * L
    for i in range(L):
        result[i] = operators.div.call([self.fetch(i), other.fetch(i)])
    return GVec(result, interface)

@operators.div.multimethod_s(Float, Vec)
@jit.unroll_safe
def Vec_div(s, self):
    return Vec_arithmetic(self, s, operators.div, lambda l, r: l / r)

@operators.div.multimethod_s(Vec, Float)
@jit.unroll_safe
def Vec_div(self, s):
    return Vec_arithmetic(self, s, operators.div, lambda l, r: l / r)

@operators.div.multimethod_s(Vec, Integer)
@jit.unroll_safe
def Vec_add(self, s):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l / r)

@operators.div.multimethod_s(Integer, Vec)
@jit.unroll_safe
def Vec_add(s, self):
    return Vec_arithmetic(self, Float(float(s.value)), operators.add, lambda l, r: l / r)

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
    result = operators.mul.call([self.fetch(0), other.fetch(0)])
    for i in range(1, L):
        result = operators.add.call([
            result,
            operators.mul.call([self.fetch(i), other.fetch(i)])
        ])
    return result

@vectormath.normalize.multimethod_s(Vec)
@jit.unroll_safe
def Vec_normalize(self):
    tosqrt = operators.mul.call([self.fetch(0), self.fetch(0)])
    for i in range(1, self.get_length()):
        tosqrt = operators.add.call([
            tosqrt, 
            operators.mul.call([self.fetch(i), self.fetch(i)])
        ])
    mag = vectormath.sqrt_.call([tosqrt])
    assert isinstance(mag, Float)
    return Vec_arithmetic(self, mag, operators.div, lambda l, r: l / r)

# @vectormath.reflect.multimethod_s(Vec, Vec)
# def Vec_reflect(i, n):
#     return operators.sub.call([
#                 i, 
#                 operators.mul.call([operators.mul.call([
#                     Float(2.0), 
#                     Vec_dot(n, i)])]),
#                 n
#             ])

# @vectormath.refract.multimethod_s(Vec, Vec, Float)
# def refract(i, n, eta):
#     ni = Vec_dot(n, i)
#     k = 1.0 - eta * eta * (1.0 - ni*ni)
#     if k < 0.0:
#         return Float(0.0)
#     else:
#         return eta * i - (eta * ni + sqrt(k)) * n

# you can wrap the stuff into a function, then implement lots of scalar behavior at once, eg.
# binary_arithmetic(Vec, operators.div, (lambda a, b: a / b))
# There's an example of that in runtime/space/operators.py

# improve to cross product (2D, 3D)
# improve to include reflect, refract
# neg
# pos

# clamp with vec, float, float
#            vec, vec, vec