from common import *

# The interface of the booleans is defined in the
# common -module, because booleans appear everywhere.

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

@method(Bool, op_cmp)
def Bool_cmp(a, b):
    if a is false and b is true:
        return fresh_integer(-1)
    elif a is true and b is false:
        return fresh_integer(+1)
    else:
        return fresh_integer(0)

@method(Bool, op_and)
def Bool_and(a, b):
    if a is true and b is true:
        return true
    else:
        return false

@method(Bool, op_or)
def Bool_or(a, b):
    if a is true or b is true:
        return true
    else:
        return false

@method(Bool, op_xor)
def Bool_xor(a, b):
    if a is true and b is true:
        return false
    elif a is true or b is true:
        return true
    else:
        return false

# This utility helps a bit if handling booleans.
def boolean(a):
    if a:
        return true
    else:
        return false
