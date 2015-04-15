from space import *
from rpython.rlib import rfile
import os

module = Module(u'fs', {}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.namespace[name] = Builtin(fn, name)
    return fn

@builtin
@signature(String)
def read_file(pathname):
    try:
        fd = rfile.create_file(as_cstring(pathname), 'r')
        try:
            return from_cstring(fd.read())
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise Error(u"%s: %s" % (pathname.string, message))
