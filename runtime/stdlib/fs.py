from space import *
from rpython.rlib import rfile
import os
from runtime import pathobj

module = Module(u'fs', {}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

@builtin
@signature(Object)
def read_file(pathname):
    pathname = pathobj.to_path(pathname)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        fd = rfile.create_file(path, 'r')
        try:
            return from_cstring(fd.read())
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise Error(u"%s: %s" % (pathname.repr(), message))
