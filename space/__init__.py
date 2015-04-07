from interface import Error, Object, null
from builtin import Builtin
from list import List
from module import Module
from multimethod import Multimethod
from numbers import Integer, Boolean
from string import String

true = Boolean(True)
false = Boolean(False)

def is_true(flag):
    return flag is not null and flag is not false

def is_false(flag):
    return flag is null or flag is false

def boolean(cond):
    return true if cond else false
