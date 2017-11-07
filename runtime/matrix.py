from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.debug import make_sure_not_resized
from rpython.rlib import jit
from space import *
from rpython.rlib.rarithmetic import r_uint, r_ulonglong

class Matrix(Object):
    def fetch(self, x, y):
        assert False, "abstract method"
        return null

    def get_dimensions(self):
        assert False, "abstract method"
        return [0, 0]

    def match_dimensions(self, other):
        D1 = self.get_dimensions()
        D2 = self.get_dimensions()
        if D1[0] != D2[0] or D1[1] != D2[2]:
            raise OldError(u"matrix dimension mismatch")
        return jit.promote(d1)

    def get_item_type(self):
        assert False, "abstract method"
        return null

    def match_interface(self, other):
        i1 = self.get_item_type()
        i2 = other.get_item_type()
        if i1 is i2:
            return i1
        raise OldError(u"matrix element type mismatch")

    def getattr(self, name):
        if name == u"length":
            D = self.get_dimensions()
            return Integer(rffi.r_long(D[0]) * rffi.r_long(D[1]))
        return Object.getattr(self, name)

    def iter(self):
        out = []
        D = self.get_dimensions()
        for y in range(D[1]):
            for x in range(D[0]):
                out.append(self.fetch(x, y))
        return List(out).iter()

class FMatrix(Matrix):
    interface = Matrix.interface
    def fetch_f(self, x, y):
        assert False, "abstract method"
        return 0.0

    def fetch(self, x, y):
        return Float(self.fetch_f(x, y))

    def get_item_type(self):
        return Float.interface

class FMatrix22(FMatrix):
    _immutable_fields_ = ['f00', 'f01', 'f10', 'f11']
    interface = Matrix.interface
    def __init__(self, f00, f01, f10, f11):
        self.f00 = f00
        self.f01 = f01
        self.f10 = f10
        self.f11 = f11

    def fetch_f(self, x, y):
        if x == 0:
            if y == 0:
                return self.f00
            elif y == 1:
                return self.f10
        elif x == 1:
            if y == 0:
                return self.f01
            elif y == 1:
                return self.f11
        raise OldError(u"float matrix access out of bounds")

    def get_dimensions(self):
        return [2, 2]

    # def repr(self):
    #     a = u"[%f %f]" % (self.f00, self.f01)
    #     b = u"[%f %f]" % (self.f10, self.f11)
    #     return u"%s\n%s\n" % (a, b)

class FMatrix33(FMatrix):
    _immutable_fields_ = ['f00', 'f01', 'f02', 'f10', 'f11', 'f12', 'f20', 'f21', 'f22']
    interface = Matrix.interface
    def __init__(self, f00, f01, f02, f10, f11, f12, f20, f21, f22):
        self.f00 = f00
        self.f01 = f01
        self.f02 = f02
        self.f10 = f10
        self.f11 = f11
        self.f12 = f12
        self.f20 = f20
        self.f21 = f21
        self.f22 = f22

    def fetch_f(self, x, y):
        if x == 0:
            if y == 0:
                return self.f00
            elif y == 1:
                return self.f10
            elif y == 2:
                return self.f20
        elif x == 1:
            if y == 0:
                return self.f01
            elif y == 1:
                return self.f11
            elif y == 2:
                return self.f21
        elif x == 2:
            if y == 0:
                return self.f02
            elif y == 1:
                return self.f12
            elif y == 2:
                return self.f22
        raise OldError(u"float matrix access out of bounds")

    def get_dimensions(self):
        return [3, 3]
    
    # def repr(self):
    #     a = u"[%f %f %f]" % (self.f00, self.f01, self.f02)
    #     b = u"[%f %f %f]" % (self.f10, self.f11, self.f12)
    #     c = u"[%f %f %f]" % (self.f20, self.f21, self.f22)
    #     return u"%s\n%s\n%s\n" % (a, b, c)

class FMatrix44(FMatrix):
    _immutable_fields_ = ['f00', 'f01', 'f02', 'f03', 'f10', 'f11', 'f12', 'f13', 'f20', 'f21', 'f22', 'f23', 'f30', 'f31', 'f32', 'f33']
    interface = Matrix.interface
    def __init__(self, f00, f01, f02, f03, f10, f11, f12, f13, f20, f21, f22, f23, f30, f31, f32, f33):
        self.f00 = f00
        self.f01 = f01
        self.f02 = f02
        self.f03 = f03
        self.f10 = f10
        self.f11 = f11
        self.f12 = f12
        self.f13 = f13
        self.f20 = f20
        self.f21 = f21
        self.f22 = f22
        self.f23 = f23
        self.f30 = f30
        self.f31 = f31
        self.f32 = f32
        self.f33 = f33

    def fetch_f(self, x, y):
        if x == 0:
            if y == 0:
                return self.f00
            elif y == 1:
                return self.f10
            elif y == 2:
                return self.f20
            elif y == 3:
                return self.f30
        elif x == 1:
            if y == 0:
                return self.f01
            elif y == 1:
                return self.f11
            elif y == 2:
                return self.f21
            elif y == 3:
                return self.f31
        elif x == 2:
            if y == 0:
                return self.f02
            elif y == 1:
                return self.f12
            elif y == 2:
                return self.f22
            elif y == 3:
                return self.f32
        elif x == 3:
            if y == 0:
                return self.f03
            elif y == 1:
                return self.f13
            elif y == 2:
                return self.f23
            elif y == 3:
                return self.f33
        raise OldError(u"float matrix access out of bounds")

    def get_dimensions(self):
        return [4, 4]

    # def repr(self):
    #     a = u"[%f %f %f %f]" % (self.f00, self.f01, self.f02, self.f03)
    #     b = u"[%f %f %f %f]" % (self.f10, self.f11, self.f12, self.f13)
    #     c = u"[%f %f %f %f]" % (self.f20, self.f21, self.f22, self.f23)
    #     d = u"[%f %f %f %f]" % (self.f30, self.f31, self.f32, self.f33)
    #     return u"%s\n%s\n%s\n%s\n" % (a, b, c, d)

class FMatrixNN(FMatrix):
    _immutable_fields_ = ['f_scalars[*]', 'rows', 'cols']
    interface = Matrix.interface
    def __init__(self, f_scalars, rows, cols):
        assert len(f_scalars) >= 4
        make_sure_not_resized(f_scalars)
        self.f_scalars = f_scalars
        self.rows = rows
        self.cols = cols

    def fetch_f(self, x, y):
        index = x + self.rows * y
        if index < len(self.f_scalars):
            return self.f_scalars[index]
        raise OldError(u"float matrix access out of bounds")

    def get_dimensions(self):
        return [self.rows, self.cols]

class GMatrix(Matrix):
    _immutable_fields_ = ['g_scalars[*]', 'rows', 'cols']
    interface = Matrix.interface
    def __init__(self, g_scalars, rows, cols, item_type):
        assert len(g_scalars) >= 4
        make_sure_not_resized(g_scalars)
        self.g_scalars = g_scalars
        self.rows = rows
        self.cols = cols
        self.item_type = item_type

    def fetch(self, x, y):
        index = x + self.rows * y
        if index < len(self.g_scalars):
            return self.g_scalars[index]
        raise OldError(u"generic vector access out of bounds")

    def get_dimensions(self):
        return [self.rows, self.cols]

@Matrix.method(u"get_element", signature(FMatrix, Integer, Integer))
def FMatrix_get_element(self, x, y):
    return Float(self.fetch_f(y.value, x.value))

@Matrix.method(u"get_element", signature(GMatrix, Integer, Integer))
def GMatrix_get_element(self, x, y):
    return self.fetch(y.value, x.value)

@jit.unroll_safe
def compact(g_scalars, rows, cols):
    if isinstance(g_scalars[0], Float):
        f_scalars = [0.0] * len(g_scalars)
        for i, val in enumerate(g_scalars):
            f_scalars[i] = to_float(val)
        return compact_f(f_scalars, rows, cols)
    interface = get_interface(g_scalars[0])
    for scalar in g_scalars:
        if get_interface(scalar) != interface:
            raise OldError(u"every element in matrix must have same interface")
    return GMatrix(g_scalars[:], rows, cols, interface)

def compact_f(f_scalars, rows, cols):
    if rows == 2 and cols == 2:
        return FMatrix22(f_scalars[0], f_scalars[1], f_scalars[2], f_scalars[3])
    elif rows == 3 and cols == 3:
        return FMatrix33(f_scalars[0], f_scalars[1], f_scalars[2], f_scalars[3], f_scalars[4], f_scalars[5], f_scalars[6], f_scalars[7], f_scalars[8])
    elif rows == 4 and cols == 4:
        return FMatrix44(f_scalars[0], f_scalars[1], f_scalars[2], f_scalars[3], f_scalars[4], f_scalars[5], f_scalars[6], f_scalars[7], f_scalars[8], f_scalars[9], f_scalars[10], f_scalars[11], f_scalars[12], f_scalars[13], f_scalars[14], f_scalars[15])
    else:
        return FMatrixNN(f_scalars, rows, cols)

@Matrix.instantiator
@jit.unroll_safe
def Matrix_init(argv):
    if len(argv) < 2:
        raise OldError(u"Too few arguments to matrix()")
    rows = []
    for a in range(len(argv)):
        if isinstance(argv[a], List):
            rows.append(argv[a])
        else:
            raise OldError(u"matrix requires args of list")
    if len(rows) < 2:
        raise OldError(u"should never happen")
    for row in rows:
        if len(row) != len(rows[0]):
            raise OldError(u"cannot have jagged matrix")
    scalars = []
    for row in rows:
        if not isinstance(row, List):
            raise OldError(u"should never happen")
        for scalar in row.contents:
            scalars.append(scalar)
    rows_len = len(rows)
    cols_len = len(rows[0])
    return compact(scalars, rows_len, cols_len)

@Matrix.method(u"determinant", signature(Matrix))
def Matrix_determinant(self):
    if isinstance(self, FMatrix22):
        return FMatrix22_determinant(self)
    if isinstance(self, FMatrix33):
        return FMatrix33_determinant(self)
    if isinstance(self, FMatrix44):
        return FMatrix44_determinant(self)
    raise OldError(u"can only take the determinant of known square matrices")

def FMatrix22_determinant(self):
    return Float(self.f00 * self.f11 - self.f10 * self.f01)

def FMatrix33_determinant(self):
    a = self.f00; b = self.f01; c = self.f02
    d = self.f10; e = self.f11; f = self.f12
    g = self.f20; h = self.f21; i = self.f22

    x = a * (e * i - f * h)
    y = b * (d * i - f * g)
    z = c * (d * h - e * g)
    return Float(x - y + z)

def FMatrix44_determinant(self):
    a = Float(self.f00); b = Float(self.f01); c = Float(self.f02); d = Float(self.f03);
    e = Float(self.f10); f = Float(self.f11); g = Float(self.f12); h = Float(self.f13);
    i = Float(self.f20); j = Float(self.f21); k = Float(self.f22); l = Float(self.f23);
    m = Float(self.f30); n = Float(self.f31); o = Float(self.f32); p = Float(self.f33);

    m1 = Matrix_init(List([List([f, g, h]), List([j, k, l]), List([n, o, p])]))
    m2 = Matrix_init(List([List([e, g, h]), List([i, k, l]), List([m, o, p])]))
    m3 = Matrix_init(List([List([e, f, h]), List([i, j, l]), List([m, n, p])]))
    m4 = Matrix_init(List([List([e, f, g]), List([i, j, k]), List([m, n, o])]))

    a1 = FMatrix33_determinant(m1).number * a.number
    b1 = FMatrix33_determinant(m2).number * b.number
    c1 = FMatrix33_determinant(m3).number * c.number
    d1 = FMatrix33_determinant(m4).number * d.number

    return Float(a1-b1+c1-d1)

@Matrix.method(u"transpose", signature(Matrix))
def Matrix_transpose(self):
    if isinstance(self, FMatrix22):
        return FMatrix22_transpose(self)
    if isinstance(self, FMatrix33):
        return FMatrix33_transpose(self)
    if isinstance(self, FMatrix44):
        return FMatrix44_transpose(self)
    raise OldError(u"can only transpose known square matrices currently")

def FMatrix22_transpose(self):
    return FMatrix22(self.f00, self.f10,
                     self.f01, self.f11)

def FMatrix33_transpose(self):
    return FMatrix33(self.f00, self.f10, self.f20,
                     self.f01, self.f11, self.f21,
                     self.f02, self.f12, self.f22)

def FMatrix44_transpose(self):
    return FMatrix44(self.f00, self.f10, self.f20, self.f30, 
                     self.f01, self.f11, self.f21, self.f31, 
                     self.f02, self.f12, self.f22, self.f32, 
                     self.f03, self.f13, self.f23, self.f33)