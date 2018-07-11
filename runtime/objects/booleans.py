from core import *

@method(BoolKind, op_eq, 1)
def Bool_eq(a, b):
    return wrap(a is b)

@method(BoolKind, op_hash, 1)
def Bool_hash(a):
    if a is true:
        return wrap(1)
    else:
        return wrap(0)

@method(BoolKind, op_cmp, 1)
def Bool_cmp(a, b):
    if a is false and b is true:
        return wrap(-1)
    elif a is true and b is false:
        return wrap(+1)
    else:
        return wrap(0)

@method(BoolKind, op_and, 1)
def Bool_and(a, b):
    return wrap(a is true and b is true)

@method(BoolKind, op_or, 1)
def Bool_or(a, b):
    return wrap(a is true or b is true)

@method(BoolKind, op_xor, 1)
def Bool_xor(a, b):
    if a is true and b is true:
        return false
    elif a is true or b is true:
        return true
    else:
        return false

@method(BoolKind, op_stringify, 1)
def Bool_stringify(a):
    if a is true:
        return String(u"true")
    else:
        return String(u"false")

variables = {
}
