import common
from rpython.rlib.objectmodel import (
    compute_hash, r_dict, specialize, always_inline)
from rpython.rlib.rarithmetic import intmask
from common import (
    Object,
    Interface,
    InterfaceNOPA,
    Constant,
    Unit, null,
    Bool, true, false,
    Integer,
    fresh_integer,
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
    op_in,
    op_getitem,
    op_setitem,
    op_iter,
    op_cmp,
    op_concat,
    op_add,
    op_sub,
    op_mul,
    op_and,
    op_or,
    op_xor,
    method,
    unique_coercion,
    has_coercion,
    convert,
    List,
    Dict,
    Set,
    Module,
    eq_fn,
    hash_fn )
from booleans import boolean
import strings

def fresh_list():
    return List([])

def fresh_dict():
    return Dict(r_dict(eq_fn, hash_fn, force_non_null=True))

def fresh_set():
    return Set(r_dict(eq_fn, hash_fn, force_non_null=True))

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
