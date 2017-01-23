from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rlib import rvmprof
from space import *
import fs

module = Module(u'vmprof', {}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

@builtin
@signature(fs.File, Float)
def enable(fileobj, interval):
    rvmprof.enable(
        rffi.r_long(fileobj.fd),
        interval.number)
    return null

@builtin
@signature()
def disable():
    rvmprof.disable()
    return null
