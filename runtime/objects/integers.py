from common import *
from rpython.rlib.rbigint import rbigint
from rpython.rlib.rstring import NumberStringParser

# Some methods for Integer
@method(Integer.interface, op_eq)
def Integer_eq(a, b):
    if a.integer_val.eq(b.integer_val):
        return true
    else:
        return false

@method(Integer.interface, op_hash)
def Integer_hash(a):
    return a

@method(Integer.interface, op_cmp)
def Integer_cmp(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    if a.integer_val.lt(b.integer_val):
        return fresh_integer(-1)
    elif a.integer_val.gt(b.integer_val):
        return fresh_integer(+1)
    else:
        return fresh_integer(0)

@method(Integer.interface, op_neg)
def Integer_neg(a):
    a = cast(a, Integer)
    return Integer(a.integer_val.neg())

@method(Integer.interface, op_pos)
def Integer_pos(a):
    return cast(a, Integer)

@method(Integer.interface, op_add)
def Integer_add(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.integer_val.add(b.integer_val))

@method(Integer.interface, op_sub)
def Integer_sub(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.integer_val.sub(b.integer_val))

@method(Integer.interface, op_mul)
def Integer_mul(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.integer_val.mul(b.integer_val))

@method(Integer.interface, op_mod)
def Integer_mod(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.integer_val.mod(b.integer_val))

@method(Integer.interface, op_and)
def Integer_and(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.integer_val.and_(b.integer_val))

@method(Integer.interface, op_or)
def Integer_or(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.integer_val.or_(b.integer_val))

@method(Integer.interface, op_xor)
def Integer_xor(a, b):
    a = cast(a, Integer)
    b = cast(b, Integer)
    return Integer(a.integer_val.xor(b.integer_val))

# TODO: The error messages here need improvement.
@method(Integer.interface, op_stringify)
def Integer_stringify(a, base=fresh_integer(10)):
    integer = cast(a, Integer).integer_val
    base = cast(base, Integer).toint()
    if base > len(digits):        # we have only 36 digits.
        raise error(e_IntegerBaseError()) # not enough digits to this base
    if base < 0:
        raise error(e_IntegerBaseError()) # negative base not supported
    return String(integer.format(digits[:base]).decode('utf-8'))

digits = "0123456789abcdefghijklmnopqrstuvwxyz"

# Needed in the evaluator. It receives integer literals as
# strings in the current structure.
def parse_integer(string, base=fresh_integer(10)):
    string = cast(string, String)
    base = cast(base, Integer).toint()
    if base > 36:        # we have only 36 digits.
        raise error(e_IntegerBaseError()) # not enough digits to this base
    if base < 0:
        raise error(e_IntegerBaseError()) # negative base not supported
    s = literal = string.string_val.encode('utf-8')
    parser = NumberStringParser(s, literal, base, 'long')
    return Integer(rbigint._from_numberstring_parser(parser))
