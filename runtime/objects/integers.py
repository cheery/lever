from core import *
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import NumberStringParser

# Some methods for Integer
@method(Integer, op_eq, 1)
def Integer_eq(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return wrap(a.bignum.eq(b.bignum))

@method(Integer, op_hash, 1)
def Integer_hash(a):
    a = cast(a, Integer)
    return a

@method(Integer, op_cmp, 1)
def Integer_cmp(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    if a.bignum.lt(b.bignum):
        return wrap(-1)
    elif a.bignum.gt(b.bignum):
        return wrap(+1)
    else:
        return wrap(0)

@method(Integer, op_neg, 1)
def Integer_neg(a):
    a = cast(a, Integer)
    return Integer(a.bignum.neg())

@method(Integer, op_pos, 1)
def Integer_pos(a):
    return cast(a, Integer)

@method(Integer, op_add, 1)
def Integer_add(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.add(b.bignum))

@method(Integer, op_sub, 1)
def Integer_sub(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.sub(b.bignum))

@method(Integer, op_mul, 1)
def Integer_mul(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.mul(b.bignum))

@method(Integer, op_mod, 1)
def Integer_mod(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.mod(b.bignum))

@method(Integer, op_floordiv, 1)
def Integer_floordiv(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.floordiv(b.bignum))

@method(Integer, op_divmod, 1)
def Integer_divmod(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    d, m = a.bignum.divmod(b.bignum)
    return Tuple([Integer(d), Integer(m)])

@method(Integer, op_not, 1)
def Integer_not(a):
    a = cast(a, Integer)
    return Integer(a.bignum.invert())

@method(Integer, op_and, 1)
def Integer_and(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.and_(b.bignum))

@method(Integer, op_or, 1)
def Integer_or(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.or_(b.bignum))

@method(Integer, op_xor, 1)
def Integer_xor(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.xor(b.bignum))

@method(Integer, op_shl, 1)
def Integer_shl(a, b):
    a = cast(a, Integer)
    b = unwrap_int(b)
    return Integer(a.bignum.lshift(b))

@method(Integer, op_shr, 1)
def Integer_shr(a, b):
    a = cast(a, Integer)
    b = unwrap_int(b)
    return Integer(a.bignum.rshift(b))

@method(Integer, op_abs, 1)
def Integer_abs(a):
    a = cast(a, Integer)
    return Integer(a.bignum.abs())

@method(Integer, op_pow, 1)
def Integer_pow(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.bignum.pow(b.bignum))

@method(Integer, op_stringify, 1)
def Integer_stringify(a, base=wrap(10)):
    integer = cast(a, Integer).bignum
    base = unwrap_int(base)
    if base > len(digits):              # we have only 36 digits.
        raise error(e_IntegerBaseError) # not enough digits to this base
    if base < 0:
        raise error(e_IntegerBaseError) # negative base not supported
    return String(integer.format(digits[:base]).decode('utf-8'))

digits = "0123456789abcdefghijklmnopqrstuvwxyz"

# Needed in the evaluator. It receives integer literals as
# strings in the current structure.
def parse_integer(string, base=wrap(10)):
    string = cast(string, String).string
    base = unwrap_int(base)
    if base > 36:        # we have only 36 digits.
        raise error(e_IntegerBaseError) # not enough digits to this base
    if base < 0:
        raise error(e_IntegerBaseError) # negative base not supported
    s = literal = string.encode('utf-8')
    parser = NumberStringParser(s, literal, base, 'long')
    return Integer(rbigint._from_numberstring_parser(parser))

variables = {
    u"parse_integer": builtin(1)(parse_integer),
}
