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
    e_IntegerBaseError,
    e_PartialOnArgument,
    Operator,
    op_eq,
    op_hash,
    op_call,
    op_in,
    op_getitem,
    op_setitem,
    op_iter,
    op_product,
    op_pattern,
    op_cmp,
    op_concat,
    op_neg,
    op_pos,
    op_add,
    op_sub,
    op_mul,
    op_not,
    op_and,
    op_or,
    op_xor,
    op_stringify,
    method,
    unique_coercion,
    has_coercion,
    convert,
    List,
    Dict,
    Set,
    Module,
    Iterator,
    Tuple,
    Freevar,
    new_datatype,
    new_constant,
    new_constructor,
    add_method,
    eq_fn,
    hash_fn )
from booleans import boolean
from integers import parse_integer
import strings

def fresh_list():
    return List([])

def fresh_dict():
    return Dict(r_dict(eq_fn, hash_fn, force_non_null=True))

def fresh_set():
    return Set(r_dict(eq_fn, hash_fn, force_non_null=True))
