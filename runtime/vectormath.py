from math import sqrt, sin, cos, tan, pi, acos, asin, atan, atan2, pow as powf, exp, log, e
from rpython.rlib.rrandom import Random
from rpython.rlib.rarithmetic import r_uint, r_ulonglong
from space import *
import time

abs_ = Multimethod(1)
length = Multimethod(1)
#distance = Multimethod(2)
dot = Multimethod(2)
cross = Multimethod(2)
normalize = Multimethod(1)
#reflect = Multimethod(2)
#refract = Multimethod(3)
pow_ = Multimethod(2)
operators.coerce_by_default(pow_)

class Vec3(Object):
    __slots__ = ['x', 'y', 'z']
    _immutable_fields_ = ['x', 'y', 'z']
    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def getattr(self, name):
        if name == u"x":
            return Float(self.x)
        if name == u"y":
            return Float(self.y)
        if name == u"z":
            return Float(self.z)
        if name == u"length":
            return Integer(3)
        return Object.getattr(self, name)

    def iter(self):
        return List([Float(self.x), Float(self.y), Float(self.z)]).iter()

    def repr(self):
        return u"vec3(%f, %f, %f)" % (self.x, self.y, self.z)

@Vec3.instantiator
def _(argv):
    if len(argv) > 3:
        raise OldError(u"Too many arguments to vec3")
    xyz = [0.0, 0.0, 0.0]
    for i, arg in enumerate(argv):
        xyz[i] = to_float(arg)
    return Vec3(xyz[0], xyz[1], xyz[2])

@operators.add.multimethod_s(Vec3, Vec3)
def _(self, other):
    return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

@operators.sub.multimethod_s(Vec3, Vec3)
def _(self, other):
    return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

@operators.mul.multimethod_s(Vec3, Float)
def _(self, s):
    return Vec3(self.x * s.number, self.y * s.number, self.z * s.number)

@operators.mul.multimethod_s(Float, Vec3)
def _(s, self):
    return Vec3(s.number * self.x, s.number * self.y, s.number * self.z)

@operators.div.multimethod_s(Vec3, Float)
def _(self, s):
    return Vec3(self.x / s.number, self.y / s.number, self.z / s.number)

@operators.div.multimethod_s(Float, Vec3)
def _(s, self):
    return Vec3(s.number / self.x, s.number / self.y, s.number / self.z)

@length.multimethod_s(Vec3)
def _(v):
    x, y, z = v.x, v.y, v.z
    return Float(sqrt(x*x + y*y + z*z))

#def distance(a, b):
#    return length(a - b)

@dot.multimethod_s(Vec3, Vec3)
def _(a, b):
    x0, y0, z0 = a.x, a.y, a.z
    x1, y1, z1 = b.x, b.y, b.z
    return Float(x0*x1 + y0*y1 + z0*z1)

@cross.multimethod_s(Vec3, Vec3)
def _(a, b):
    x0, y0, z0 = a.x, a.y, a.z
    x1, y1, z1 = b.x, b.y, b.z
    return Vec3(y0*z1 - z0*y1, z0*x1 - x0*z1, x0*y1 - y0*x1)

@normalize.multimethod_s(Vec3)
def _(v):
    x, y, z = v.x, v.y, v.z
    d = sqrt(x*x + y*y + z*z)
    if d > 0.0:
        return Vec3(v.x / d, v.y / d, v.z / d)
    return v

#def reflect(i, n):
#    return i - 2.0 * dot(n, i) * n
#
#def refract(i, n, eta):
#    ni = dot(n, i)
#    k = 1.0 - eta * eta * (1.0 - ni*ni)
#    return 0.0 if k < 0.0 else eta * i - (eta * ni + sqrt(k)) * n

class Quat(Object):
    __slots__ = ['x', 'y', 'z', 'w']
    _immutable_fields_ = ['x', 'y', 'z', 'w']
    def __init__(self, x, y, z, w):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    def getattr(self, name):
        if name == u"x":
            return Float(self.x)
        if name == u"y":
            return Float(self.y)
        if name == u"z":
            return Float(self.z)
        if name == u"w":
            return Float(self.w)
        if name == u"length":
            return Integer(4)
        return Object.getattr(self, name)

    def iter(self):
        return List([Float(self.x), Float(self.y), Float(self.z), Float(self.w)]).iter()

@Quat.instantiator
def _(argv):
    if len(argv) > 4:
        raise OldError(u"Too many arguments to quat")
    xyz = [0.0, 0.0, 0.0, 1.0]
    for i, arg in enumerate(argv):
        xyz[i] = to_float(arg)
    return Quat(xyz[0], xyz[1], xyz[2], xyz[3])

@Quat.builtin_method
def to_mat4(argv):
    if len(argv) < 1:
        raise OldError(u"Too few arguments")
    q = argv[0]
    if not isinstance(q, Quat):
        raise OldError(u"Expected quaternion")
    if len(argv) > 1:
        p = argv[1]
        if not isinstance(p, Vec3):
            raise OldError(u"Expected vec3 as argument")
        x, y, z = p.x, p.y, p.z
    else:
        x = y = z = 0.0
    sqx = q.x*q.x
    sqy = q.y*q.y
    sqz = q.z*q.z
    sqw = q.w*q.w
    # inverse only required if quaternion not normalized
    invs = 1 / (sqx + sqy + sqz + sqw)
    m00 = ( sqx - sqy - sqz + sqw)*invs
    m11 = (-sqx + sqy - sqz + sqw)*invs
    m22 = (-sqx - sqy + sqz + sqw)*invs
    tmp1 = q.x*q.y
    tmp2 = q.z*q.w
    m10 = 2.0 * (tmp1 + tmp2)*invs
    m01 = 2.0 * (tmp1 - tmp2)*invs
    tmp1 = q.x*q.z
    tmp2 = q.y*q.w
    m20 = 2.0 * (tmp1 - tmp2)*invs
    m02 = 2.0 * (tmp1 + tmp2)*invs
    tmp1 = q.y*q.z
    tmp2 = q.x*q.w
    m21 = 2.0 * (tmp1 + tmp2)*invs
    m12 = 2.0 * (tmp1 - tmp2)*invs
    return Mat4([
        m00, m10, m20, 0.0,
        m01, m11, m21, 0.0,
        m02, m12, m22, 0.0,
        x,   y,   z,   1.0])
    


@Quat.builtin_method
@signature(Quat)
def invert(self):
    dot = sqrt(self.x*self.x + self.y*self.y + self.z*self.z + self.w*self.w)
    invDot = 1.0 / dot if dot > 0.0 else 0.0
    return Quat(-self.x*invDot, -self.y*invDot, -self.z*invDot, self.w*invDot)

@operators.neg.multimethod_s(Vec3)
def _(self):
    return Vec3(-self.x, -self.y, -self.z)

@operators.neg.multimethod_s(Quat)
def _(self):
    return Quat(-self.x, -self.y, -self.z, self.w)

@operators.pos.multimethod_s(Vec3)
def _(self):
    return self

@operators.pos.multimethod_s(Quat)
def _(self):
    return self

@operators.mul.multimethod_s(Quat, Quat)
def _(self, other):
    ax, ay, az, aw = self.x, self.y, self.z, self.w
    bx, by, bz, bw = other.x, other.y, other.z, other.w
    return Quat(
        ax * bw + aw * bx + ay * bz - az * by,
        ay * bw + aw * by + az * bx - ax * bz,
        az * bw + aw * bz + ax * by - ay * bx,
        aw * bw - ax * bx - ay * by - az * bz)

@operators.mul.multimethod_s(Quat, Vec3)
def _(self, other):
    qx, qy, qz, qw = self.x, self.y, self.z, self.w
    x, y, z = other.x, other.y, other.z
    ix = qw * x + qy * z - qz * y
    iy = qw * y + qz * x - qx * z
    iz = qw * z + qx * y - qy * x
    iw = -qx * x - qy * y - qz * z
    return Vec3(
        ix * qw + iw * -qx + iy * -qz - iz * -qy,
        iy * qw + iw * -qy + iz * -qx - ix * -qz,
        iz * qw + iw * -qz + ix * -qy - iy * -qx)

@Builtin
@signature(Vec3, Float)
def axisangle(v, angle):
    angle = to_float(angle)
    x, y, z = v.x, v.y, v.z
    s = sin(angle * 0.5)
    return Quat(s*x, s*y, s*z, cos(angle * 0.5))

class Mat4(Object):
    __slots__ = ['values']
    _immutable_fields_ = ['values[*]']
    def __init__(self, values):
        self.values = list(values)

    def getattr(self, name):
        if name == u"length":
            return Integer(16)
        return Object.getattr(self, name)

    def iter(self):
        seq = []
        for x in self.values:
            seq.append(Float(x))
        return List(seq).iter()

    #def __repr__(self):
    #    return "mat4({})".format(self.values)

@Mat4.instantiator
def _(argv):
    if len(argv) > 16:
        raise OldError(u"Too many arguments to mat4")
    mat = [1.0, 0.0, 0.0, 0.0,
           0.0, 1.0, 0.0, 0.0,
           0.0, 0.0, 1.0, 0.0,
           0.0, 0.0, 0.0, 1.0]
    for i, arg in enumerate(argv):
        mat[i] = to_float(arg)
    return Mat4(mat)

@Mat4.builtin_method
@signature(Mat4)
def transpose(self):
    a = self.values
    return Mat4([a[0], a[4], a[8], a[12], a[1], a[5], a[9], a[13], a[2], a[6], a[10], a[14], a[3], a[7], a[11], a[15]])

@Mat4.builtin_method
@signature(Mat4)
def invert(self):
    a = self.values
    a00 = a[0]; a01 = a[1]; a02 = a[2]; a03 = a[3];
    a10 = a[4]; a11 = a[5]; a12 = a[6]; a13 = a[7];
    a20 = a[8]; a21 = a[9]; a22 = a[10]; a23 = a[11];
    a30 = a[12]; a31 = a[13]; a32 = a[14]; a33 = a[15];

    b00 = a00 * a11 - a01 * a10
    b01 = a00 * a12 - a02 * a10
    b02 = a00 * a13 - a03 * a10
    b03 = a01 * a12 - a02 * a11
    b04 = a01 * a13 - a03 * a11
    b05 = a02 * a13 - a03 * a12
    b06 = a20 * a31 - a21 * a30
    b07 = a20 * a32 - a22 * a30
    b08 = a20 * a33 - a23 * a30
    b09 = a21 * a32 - a22 * a31
    b10 = a21 * a33 - a23 * a31
    b11 = a22 * a33 - a23 * a32
    det = b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06
    if det == 0.0:
        return None
    det = 1.0 / det

    return Mat4([
        (a11 * b11 - a12 * b10 + a13 * b09) * det,
        (a02 * b10 - a01 * b11 - a03 * b09) * det,
        (a31 * b05 - a32 * b04 + a33 * b03) * det,
        (a22 * b04 - a21 * b05 - a23 * b03) * det,
        (a12 * b08 - a10 * b11 - a13 * b07) * det,
        (a00 * b11 - a02 * b08 + a03 * b07) * det,
        (a32 * b02 - a30 * b05 - a33 * b01) * det,
        (a20 * b05 - a22 * b02 + a23 * b01) * det,
        (a10 * b10 - a11 * b08 + a13 * b06) * det,
        (a01 * b08 - a00 * b10 - a03 * b06) * det,
        (a30 * b04 - a31 * b02 + a33 * b00) * det,
        (a21 * b02 - a20 * b04 - a23 * b00) * det,
        (a11 * b07 - a10 * b09 - a12 * b06) * det,
        (a00 * b09 - a01 * b07 + a02 * b06) * det,
        (a31 * b01 - a30 * b03 - a32 * b00) * det,
        (a20 * b03 - a21 * b01 + a22 * b00) * det])

@Mat4.builtin_method
@signature(Mat4)
def adjoint(self):
    a = self.values
    a00 = a[0]; a01 = a[1]; a02 = a[2]; a03 = a[3];
    a10 = a[4]; a11 = a[5]; a12 = a[6]; a13 = a[7];
    a20 = a[8]; a21 = a[9]; a22 = a[10]; a23 = a[11];
    a30 = a[12]; a31 = a[13]; a32 = a[14]; a33 = a[15];
    return Mat4([
         (a11 * (a22 * a33 - a23 * a32) - a21 * (a12 * a33 - a13 * a32) + a31 * (a12 * a23 - a13 * a22)),
        -(a01 * (a22 * a33 - a23 * a32) - a21 * (a02 * a33 - a03 * a32) + a31 * (a02 * a23 - a03 * a22)),
         (a01 * (a12 * a33 - a13 * a32) - a11 * (a02 * a33 - a03 * a32) + a31 * (a02 * a13 - a03 * a12)),
        -(a01 * (a12 * a23 - a13 * a22) - a11 * (a02 * a23 - a03 * a22) + a21 * (a02 * a13 - a03 * a12)),
        -(a10 * (a22 * a33 - a23 * a32) - a20 * (a12 * a33 - a13 * a32) + a30 * (a12 * a23 - a13 * a22)),
         (a00 * (a22 * a33 - a23 * a32) - a20 * (a02 * a33 - a03 * a32) + a30 * (a02 * a23 - a03 * a22)),
        -(a00 * (a12 * a33 - a13 * a32) - a10 * (a02 * a33 - a03 * a32) + a30 * (a02 * a13 - a03 * a12)),
         (a00 * (a12 * a23 - a13 * a22) - a10 * (a02 * a23 - a03 * a22) + a20 * (a02 * a13 - a03 * a12)),
         (a10 * (a21 * a33 - a23 * a31) - a20 * (a11 * a33 - a13 * a31) + a30 * (a11 * a23 - a13 * a21)),
        -(a00 * (a21 * a33 - a23 * a31) - a20 * (a01 * a33 - a03 * a31) + a30 * (a01 * a23 - a03 * a21)),
         (a00 * (a11 * a33 - a13 * a31) - a10 * (a01 * a33 - a03 * a31) + a30 * (a01 * a13 - a03 * a11)),
        -(a00 * (a11 * a23 - a13 * a21) - a10 * (a01 * a23 - a03 * a21) + a20 * (a01 * a13 - a03 * a11)),
        -(a10 * (a21 * a32 - a22 * a31) - a20 * (a11 * a32 - a12 * a31) + a30 * (a11 * a22 - a12 * a21)),
         (a00 * (a21 * a32 - a22 * a31) - a20 * (a01 * a32 - a02 * a31) + a30 * (a01 * a22 - a02 * a21)),
        -(a00 * (a11 * a32 - a12 * a31) - a10 * (a01 * a32 - a02 * a31) + a30 * (a01 * a12 - a02 * a11)),
         (a00 * (a11 * a22 - a12 * a21) - a10 * (a01 * a22 - a02 * a21) + a20 * (a01 * a12 - a02 * a11))])

@Mat4.builtin_method
@signature(Mat4)
def determinant(self):
    a = self.values
    a00 = a[0]; a01 = a[1]; a02 = a[2]; a03 = a[3];
    a10 = a[4]; a11 = a[5]; a12 = a[6]; a13 = a[7];
    a20 = a[8]; a21 = a[9]; a22 = a[10]; a23 = a[11];
    a30 = a[12]; a31 = a[13]; a32 = a[14]; a33 = a[15];
    b00 = a00 * a11 - a01 * a10
    b01 = a00 * a12 - a02 * a10
    b02 = a00 * a13 - a03 * a10
    b03 = a01 * a12 - a02 * a11
    b04 = a01 * a13 - a03 * a11
    b05 = a02 * a13 - a03 * a12
    b06 = a20 * a31 - a21 * a30
    b07 = a20 * a32 - a22 * a30
    b08 = a20 * a33 - a23 * a30
    b09 = a21 * a32 - a22 * a31
    b10 = a21 * a33 - a23 * a31
    b11 = a22 * a33 - a23 * a32
    return Float(b00 * b11 - b01 * b10 + b02 * b09 + b03 * b08 - b04 * b07 + b05 * b06)

@Mat4.builtin_method
@signature(Mat4, Vec3)
def rotate_vec3(self, v):
    a = self.values
    x, y, z = v.x, v.y, v.z
    return Vec3(
        a[0]*x + a[4]*y + a[8]*z,
        a[1]*x + a[5]*y + a[9]*z,
        a[2]*x + a[6]*y + a[10]*z)

@operators.mul.multimethod_s(Mat4, Vec3)
def _(self, other):
    a = self.values
    a00 = a[0]; a01 = a[1]; a02 = a[2]; a03 = a[3];
    a10 = a[4]; a11 = a[5]; a12 = a[6]; a13 = a[7];
    a20 = a[8]; a21 = a[9]; a22 = a[10]; a23 = a[11];
    a30 = a[12]; a31 = a[13]; a32 = a[14]; a33 = a[15];
    x, y, z = other.x, other.y, other.z
    return Vec3(
        a00*x + a10*y + a20*z + a30,
        a01*x + a11*y + a21*z + a31,
        a02*x + a12*y + a22*z + a32)

@operators.mul.multimethod_s(Mat4, Mat4)
def _(self, other):
    a = self.values
    a00 = a[0]; a01 = a[1]; a02 = a[2]; a03 = a[3];
    a10 = a[4]; a11 = a[5]; a12 = a[6]; a13 = a[7];
    a20 = a[8]; a21 = a[9]; a22 = a[10]; a23 = a[11];
    a30 = a[12]; a31 = a[13]; a32 = a[14]; a33 = a[15];
    b = other.values
    out = [0.0] * 16
    b0  = b[0]; b1 = b[1]; b2 = b[2]; b3 = b[3];
    out[0] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[1] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[2] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[3] = b0*a03 + b1*a13 + b2*a23 + b3*a33

    b0 = b[4]; b1 = b[5]; b2 = b[6]; b3 = b[7];
    out[4] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[5] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[6] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[7] = b0*a03 + b1*a13 + b2*a23 + b3*a33

    b0 = b[8]; b1 = b[9]; b2 = b[10]; b3 = b[11];
    out[8] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[9] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[10] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[11] = b0*a03 + b1*a13 + b2*a23 + b3*a33

    b0 = b[12]; b1 = b[13]; b2 = b[14]; b3 = b[15];
    out[12] = b0*a00 + b1*a10 + b2*a20 + b3*a30
    out[13] = b0*a01 + b1*a11 + b2*a21 + b3*a31
    out[14] = b0*a02 + b1*a12 + b2*a22 + b3*a32
    out[15] = b0*a03 + b1*a13 + b2*a23 + b3*a33
    return Mat4(out)

@Mat4.builtin_method
@signature(Mat4, Vec3)
def translate(self, v):
    x, y, z = v.x, v.y, v.z
    a = self.values
    return Mat4(a[0:12] + [
        a[0] * x + a[4] * y + a[8] * z + a[12],
        a[1] * x + a[5] * y + a[9] * z + a[13],
        a[2] * x + a[6] * y + a[10] * z + a[14],
        a[3] * x + a[7] * y + a[11] * z + a[15]])

@Mat4.builtin_method
@signature(Mat4, Vec3)
def scale(self, v):
    x, y, z = v.x, v.y, v.z
    a = self.values
    return Mat4([a[0]*x, a[1]*x, a[2]*x, a[3]*x, a[4]*y, a[5]*y, a[6]*y, a[7]*y, a[8]*z, a[9]*z, a[10]*z, a[11]*z, a[12], a[13], a[14], a[15]])

@operators.clamp.multimethod_s(Float, Float, Float)
def clamp(x, low, high):
    return Float(min(max(x.number, low.number), high.number))

@operators.clamp.multimethod_s(Integer, Integer, Integer)
def clamp(x, low, high):
    return Integer(min(max(x.value, low.value), high.value))

# This may move into stdlib module eventually, possibly.
random = Random()
masklower = r_ulonglong(0xffffffff)

# This code might break again if r_ulonglong is treated as 32-bit int.
def init_random():
    n = r_ulonglong(time.time())
    key = []
    while n > 0:
        key.append(r_uint(n & masklower))
        n >>= 32
    if len(key) == 0:
        key.append(r_uint(0))
    random.init_by_array(key)

@abs_.multimethod_s(Float)
def abs_float(f):
    return Float(-f.number) if f.number < 0.0 else f

@abs_.multimethod_s(Integer)
def abs_int(i):
    return Integer(-i.value) if i.value < 0 else i

@Builtin
@signature()
def random_():
    return Float(random.random())

@Builtin
@signature()
def random_circle():
    r = random.random() * 2.0 * pi
    return Vec3(cos(r), sin(r), 0.0)

@Builtin
@signature()
def random_sphere():
    r = random.random() * 2.0 * pi
    z = (random.random() * 2.0) - 1.0
    s = sqrt(1.0 - z*z)
    return Vec3(cos(r) * s, sin(r) * s, z)

# These may also belong somewhere else, but they start here.
@Builtin
@signature(Float)
def sin_(f):
    return Float(sin(f.number))

@Builtin
@signature(Float)
def cos_(f):
    return Float(cos(f.number))

@Builtin
@signature(Float)
def tan_(f):
    return Float(tan(f.number))

@Builtin
@signature(Float)
def asin_(f):
    return Float(asin(f.number))

@Builtin
@signature(Float)
def acos_(f):
    return Float(acos(f.number))

@Builtin
@signature(Float)
def atan_(f):
    return Float(atan(f.number))

@Builtin
@signature(Float, Float)
def atan2_(y, x):
    return Float(atan2(y.number, x.number))

@Builtin
@signature(Float)
def sqrt_(f):
    return Float(sqrt(f.number))

@pow_.multimethod_s(Float, Float)
def pow_float(a, b):
    try:
        return Float(powf(a.number, b.number))
    except OverflowError as ovf:
        raise unwind(LError(u"math range error"))
    except ValueError as val:
        raise unwind(LError(u"math domain error"))

@pow_.multimethod_s(Integer, Integer)
def pow_int(a, b):
    try:
        return Integer(powi(a.value, b.value))
    except OverflowError as ovf:
        raise unwind(LError(u"math range error"))
    except ValueError as val:
        raise unwind(LError(u"math domain error"))

def powi(iv, iw):
    temp = iv
    ix = 1
    while iw > 0:
        if iw & 1:
            ix = ix * temp
        iw >>= 1   # Shift exponent down by 1 bit
        if iw == 0:
            break
        temp = temp * temp # Square the value of temp
    return ix

@Builtin
@signature(Float)
def exp_(a):
    return Float(exp(a.number))

@Builtin
@signature(Float, Float)
def log_(a, b):
    return Float(log(a.number) / log(b.number))

@Builtin
@signature(Float)
def ln(a):
    return Float(log(a.number))

@Builtin
@signature(Float)
def sign(f):
    if f.number < 0.0:
        return Float(-1.0)
    elif f.number > 0.0:
        return Float(+1.0)
    else:
        return Float(0.0)

#acos, asin, atan, atan2

@Builtin
@signature(Object, Object, Object, Object)
def projection_matrix(fovy, aspect, znear, zfar):
    fovy = to_float(fovy)
    aspect = to_float(aspect)
    znear = to_float(znear)
    zfar = to_float(zfar)
    f = 1/tan(fovy/2.0)
    zd = znear-zfar
    return Mat4([
        f/aspect, 0.0,  0.0,                 0.0,
        0.0,        f,  0.0,                 0.0,
        0.0,      0.0,  (zfar+znear) / zd,   -1.0,
        0.0,      0.0,  (2*zfar*znear) / zd, 0.0
    ])

by_symbol = {
    u"vec3": Vec3.interface,
    u"quat": Quat.interface,
    u"mat4": Mat4.interface,
    u"left":     Vec3(-1.0, 0.0, 0.0),
    u"right":    Vec3(+1.0, 0.0, 0.0),
    u"up":       Vec3( 0.0,+1.0, 0.0),
    u"down":     Vec3( 0.0,-1.0, 0.0),
    u"forward":  Vec3( 0.0, 0.0,+1.0),
    u"backward": Vec3( 0.0, 0.0,-1.0),
    u"axisangle": axisangle,
    u"random":        random_,
    u"random_circle": random_circle,
    u"random_sphere": random_sphere,
    u"length":    length,
    u"dot":       dot,
    u"cross":     cross,
    u"normalize": normalize,
    u"sin":       sin_,
    u"cos":       cos_,
    u"tan":       tan_,
    u"sqrt":      sqrt_,
    u"pi":        Float(pi),
    u"tau":       Float(pi*2),
    u"projection_matrix": projection_matrix,
    u"abs":       abs_,
    u"sign":      sign,
    u"pow":       pow_,
    u"exp":       exp_,
    u"log":       log_,
    u"ln":        ln,
    u"e":         Float(e),
}
