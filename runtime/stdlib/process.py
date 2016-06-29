from rpython.rlib import rstring
from space import *
import pathobj
import os, sys

module = Module(u'process', {}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

if sys.platform == "win32":
    @builtin
    @signature(Object, List)
    def spawnv(path, args): 
        path, argv = build_path_args(path, args)
        pid = os.spawnv(os.P_NOWAIT, path, argv)
        return Integer(pid)
else:
    @builtin
    @signature(Object, List)
    def spawnv(path, args): 
        path, argv = build_path_args(path, args)
        pid = os.fork()
        if pid == 0:
            os.execv(path, argv)
        return Integer(pid)

def build_path_args(path, args):
    pathname = pathobj.to_path(path)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    if '\x00' in path:
        raise OldError(u"NUL byte in spawnv path string")
    argv = []
    for arg in args.contents:
        if isinstance(arg, pathobj.Path):
            a = pathobj.os_stringify(arg).encode('utf-8')
        else:
            a = as_cstring(arg)
        if '\x00' in a:
            raise OldError(u"NUL byte in spawnv arg string")
        argv.append(rstring.assert_str0(a))
    return rstring.assert_str0(path), argv

@builtin
@signature(Integer)
def waitpid(pid):
    return Integer(os.waitpid(int(pid.value), 0)[1])

@builtin
@signature(Object)
def which(program):
    if isinstance(program, String):
        if program.string.count(u"/") > 0:
            program = pathobj.to_path(program)
    if isinstance(program, pathobj.Path):
        path = pathobj.os_stringify(program).encode('utf-8')
        if is_exe(path):
            return pathobj.concat(pathobj.getcwd(), program)
        return null
    elif not isinstance(program, String):
        raise OldError(u"string or path expected to .which()")
    program = as_cstring(program)
    for path in os.environ.get("PATH").split(os.pathsep):
        path = path.strip('"')
        exe_file = os.path.join(path, program)
        if is_exe(exe_file):
            return from_cstring(exe_file)
    return null

def is_exe(fpath):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)
