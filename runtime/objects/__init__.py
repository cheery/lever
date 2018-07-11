import core
import booleans
import chaff
import dicts
import integers
import lists
import modules
import sets
import strings
import slots

variables = {}
variables.update(core.variables)
variables.update(booleans.variables)
variables.update(chaff.variables)
variables.update(dicts.variables)
variables.update(integers.variables)
variables.update(lists.variables)
variables.update(modules.variables)
variables.update(sets.variables)
variables.update(strings.variables)
variables.update(slots.variables)

#import common
#from common import (
#    Object,
#    Interface,
#    InterfaceParametric,
#    Constant,
#    Bool, true, false,
#    Integer,
#    fresh_integer,
#    String,
#    FunctionInterface,
#    FunctionMemo,
#    func_interfaces,
#    builtin_interfaces,
#    Builtin,
#    call,
#    callv,
#    prefill,
#    builtin,
#    python_bridge,
#    cast,
#    error,
#    Traceback,
#    e_TypeError,
#    e_IOError,
#    e_JSONDecodeError,
#    e_IntegerParseError,
#    e_EvalError,
#    e_IntegerBaseError,
#    e_PartialOnArgument,
#    e_NoItems,
#    e_NoIndex,
#    e_NoValue,
#    e_AssertTriggered,
#    Operator,
#    op_eq,
#    op_hash,
#    op_in,
#    op_getitem,
#    op_setitem,
#    op_getslot,
#    op_setslot,
#    op_iter,
#    op_product,
#    op_pattern,
#    op_cmp,
#    op_concat,
#    op_copy,
#    op_neg,
#    op_pos,
#    op_add,
#    op_sub,
#    op_mul,
#    op_mod,
#    op_not,
#    op_and,
#    op_or,
#    op_xor,
#    op_stringify,
#    method,
#    getter,
#    setter,
#    attr_method,
#    unique_coercion,
#    has_coercion,
#    convert,
#    List,
#    Dict,
#    Set,
#    Module,
#    ModuleSpace,
#    w_import,
#    Iterator,
#    Tuple,
#    Freevar,
#    new_datatype,
#    new_constant,
#    new_constructor,
#    add_method,
#    add_attr,
#    add_attr_method,
#    eq_fn,
#    hash_fn,
#    TypeParameter,
#    w_by_reference,
#    w_by_value )
#from integers import parse_integer
#from dicts import construct_dict, fresh_dict
#from sets import construct_set, fresh_set
#from records import (
#    construct_record )
