# There is a convenient PYPYLOG=jit-log-opt:logfile
# to enable jit logging from outside.
# But I like having the option to
# enable it from the inside.
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rlib.rjitlog import rjitlog
from rpython.rlib import jit
from space import *
import fs

module = Module(u'jitlog', {}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

@builtin
@signature(fs.File)
def enable(fileobj):
    try:
        rjitlog.enable_jitlog(rffi.r_long(fileobj.fd))
    except rjitlog.JitlogError as error:
        raise unwind(LError(
            error.msg.decode('utf-8')))
    return null

@builtin
@signature()
@jit.dont_look_inside
def disable():
    rjitlog.disable_jitlog()
    return null
