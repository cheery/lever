import common
from rpython.rlib.objectmodel import (
    compute_hash, r_dict, specialize, always_inline)
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rbigint import rbigint
from common import (
    Object,
    Interface,
    InterfaceNOPA,
    Constant,
    Unit, null,
    Bool, true, false,
    Integer,
    String,
    FunctionInterface,
    FunctionMemo,
    func_interfaces,
    builtin_interfaces,
    Builtin,
    call,
    builtin,
    python_bridge,
    cast,
    error,
    Traceback,
    e_TypeError,
    e_IOError,
    e_JSONDecodeError,
    e_IntegerParseError,
    e_EvalError,
    Operator,
    op_eq,
    op_hash,
    op_call,
    method,
    unique_coercion,
    has_coercion,
    convert,
    List,
    Dict,
    Set,
    Module )

def fresh_integer(val):
    return Integer(rbigint.fromint(val))

def fresh_list():
    return List([])

def fresh_dict():
    return Dict(r_dict(eq_fn, hash_fn, force_non_null=True))

def fresh_set():
    return Set(r_dict(eq_fn, hash_fn, force_non_null=True))

def eq_fn(a, b):
    result = convert(call(op_eq, [a,b]), Bool)
    if result is true:
        return true
    else:
        return false

def hash_fn(a):
    result = call(op_hash, [a])
    return intmask(cast(result, Integer).toint())

# All methods for Unit
@method(Unit, op_eq)
def Unit_eq(a, b):
    return true

@method(Unit, op_hash)
def Unit_hash(a):
    return fresh_integer(0)

# All methods for Bool
@method(Bool, op_eq)
def Bool_eq(a, b):
    if a is b:
        return true
    else:
        return false

@method(Bool, op_hash)
def Bool_hash(a):
    if a is true:
        return fresh_integer(1)
    else:
        return fresh_integer(0)

# Some methods for Integer
@method(Integer.interface, op_eq)
def Integer_eq(a, b):
    if a.integer_val == b.integer_val:
        return true
    else:
        return false

@method(Integer.interface, op_hash)
def Integer_hash(a):
    return a

# Some methods for String
@method(String.interface, op_eq)
def String_eq(a, b):
    if a.string_val == b.string_val:
        return true
    else:
        return false

@method(String.interface, op_hash)
def String_hash(a):
    return fresh_integer(compute_hash(a.string_val))

# Needed in the evaluator. It receives integer literals as
# strings in the current structure.
# TODO: The error messages here need improvement.
def parse_integer(string, base=None):
    string = cast(string, String)
    base = 10 if base is None else cast(base, Integer).toint()
    value = 0
    for ch in string.string_val:
        if u'0' <= ch and ch <= u'9':
            digit = ord(ch) - ord('0')
        elif u'a' <= ch and ch <= u'z':
            digit = ord(ch) - ord('a') + 10
        elif u'A' <= ch and ch <= u'Z':
            digit = ord(ch) - ord('A') + 10
        else:
            raise error(e_EvalError()) #u"invalid digit char: " + ch))
        if digit >= base:
            raise error(e_EvalError()) #u"invalid digit char: " + ch))
        value = value * base + digit
    return fresh_integer(value)
