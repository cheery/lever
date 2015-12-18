from rpython.rlib import rgc, jit
from space import *

module = Module(u"gc", {
}, frozen=True)

def builtin(fn):
    module.setattr_force(fn.__name__.decode('utf-8'), Builtin(fn))
    return fn

@builtin
@signature()
@jit.dont_look_inside
def collect():
    rgc.collect()
    return null
