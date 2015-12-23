from rpython.rlib import rgc, jit
from space import *

module = Module(u"gc", {
}, frozen=True)

def builtin(fn):
    module.setattr_force(fn.__name__.decode('utf-8'), Builtin(fn))
    return fn

# I'm not sure how to introduce this into program that can be JIT
# @builtin
# @signature()
# @jit.dont_look_inside did not work
# def collect():
#     rgc.collect()
#     return null
