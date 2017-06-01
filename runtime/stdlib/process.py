from rpython.rlib import rstring
from space import *
import pathobj
import os, sys
from async_io import *
from uv_handle import Handle2, check
import uv_stream
import rlibuv as uv

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

@builtin
@signature(Integer, Integer)
def kill_(pid, signum):
    check( uv.kill(pid.value, signum.value) )
    return null

class Spawn(Handle2):
    def __init__(self, process):
        Handle2.__init__(self,
            rffi.cast(uv.handle_ptr, process))
        self.process = process
        self.on_exit = Event()
        self.events += [self.on_exit]

    def getattr(self, name):
        if name == u"on_exit":
            return self.on_exit
        return Handle2.getattr(self, name)

@Spawn.instantiator2(signature(Dict))
def Spawn_init(options):
    ec = core.get_ec()
    flags = 0
    c_options = lltype.malloc(
        uv.process_options_ptr.TO,
        flavor='raw', zero=True)
    c_options.c_exit_cb = rffi.llhelper(uv.exit_cb,
        _on_exit_)
    c_args_c = 0
    try:
        name = String(u"file")
        p = cast(options.getitem(name), pathobj.Path, u".file") 
        p = pathobj.os_stringify(p).encode('utf-8')
        c_options.c_file = rffi.str2charp(p)

        name = String(u"args")
        a = cast(options.getitem(name), List, u".args") 
        c_args_c = len(a.contents)
        c_options.c_args = lltype.malloc(rffi.CCHARPP.TO,
            c_args_c+1, flavor='raw', zero=True)
        for i in range(c_args_c):
            s = cast(a.contents[i], String, u".args[i]") 
            s = s.string.encode('utf-8')
            c_options.c_args[i] = rffi.str2charp(s)
        # TODO: the env variables are provided weirdly.
        #       figure out what the actual rules are here.
        #c_options.c_env = CCHARPP
        name = String(u"cwd")
        if options.contains(name):
            c = cast(options.getitem(name), pathobj.Path, u".cwd") 
            c = pathobj.os_stringify(c).encode('utf-8')
            c_options.c_cwd = rffi.str2charp(p)
        name = String(u"stdio")
        if options.contains(name):
            e = cast(options.getitem(name), List, u".stdio") 
            c_options.c_stdio_count = rffi.cast(rffi.INT, len(e.contents))
            c_options.c_stdio = lltype.malloc(
                rffi.CArrayPtr(uv.stdio_container_t).TO, c_options.c_stdio_count,
                flavor='raw', zero=True)
            for i in range(c_options.c_stdio_count):
                if e.contents[i] == null:
                    c_options.c_stdio[i].c_flags = rffi.cast(rffi.UINT, uv.IGNORE)
                    continue
                o = cast(e.contents[i], Dict, u".stdio[i]")
                set_stdio(c_options.c_stdio[i], o)
        name = String(u"uid")
        if options.contains(name):
            n = cast(options.getitem(name), Integer, u".uid") 
            c_options.c_uid = rffi.cast(rffi.UINT, n.value)
            flags |= uv.PROCESS_SETUID
        name = String(u"gid")
        if options.contains(name):
            n = cast(options.getitem(name), Integer, u".gid") 
            c_options.c_gid = rffi.cast(rffi.UINT, n.value)
            flags |= uv.PROCESS_SETGID
        name = String(u"windows_verbatim_arguments")
        if options.contains(name):
            if is_true(options.getitem(name)):
                flags |= uv.PROCESS_WINDOWS_VERBATIM_ARGUMENTS
        name = String(u"detached")
        if options.contains(name):
            if is_true(options.getitem(name)):
                flags |= uv.PROCESS_DETACHED
        name = String(u"windows_hide")
        if options.contains(name):
            if is_true(options.getitem(name)):
                flags |= uv.PROCESS_WINDOWS_HIDE
        c_options.c_flags = rffi.cast(rffi.UINT, flags)
        process = ec.handles.create(uv.process_ptr,
            uv.spawn, c_options)
    finally:
        if c_options.c_stdio:
            lltype.free(c_options.c_stdio, flavor='raw')
        if c_options.c_cwd:
            lltype.free(c_options.c_cwd, flavor='raw')
        if c_options.c_args:
            for i in range(c_args_c):
                if c_options.c_args[i]:
                    lltype.free(c_options.c_args[i], flavor='raw')
            lltype.free(c_options.c_args, flavor='raw')
        if c_options.c_file:
            lltype.free(c_options.c_file, flavor='raw')
        lltype.free(c_options, flavor="raw")
    return Spawn(process)

# logic of how the c_data type is determined in libuv.
#mask = uv.CREATE_PIPE | uv.INHERIT_FD | uv.INHERIT_STREAM
#flags & mask
#uv.CREATE_PIPE -> stream
#uv.INHERIT_FD -> fd
#uv.INHERIT_STREAM -> stream
def set_stdio(stdio, obj):
    c_flags = 0
    name = String(u"readable")
    if obj.contains(name):
        if is_true(obj.getitem(name)):
            c_flags |= uv.READABLE_PIPE
    name = String(u"writable")
    if obj.contains(name):
        if is_true(obj.getitem(name)):
            c_flags |= uv.WRITABLE_PIPE
    int_ok = True
    name = String(u"create")
    if obj.contains(name):
        if is_true(obj.getitem(name)):
            c_flags |= uv.CREATE_PIPE
            int_ok = False
    fd_obj = obj.getitem(String(u"fd"))
    if int_ok and isinstance(fd_obj, Integer):
        c_flags |= uv.INHERIT_FD
        uv.set_stdio_fd(stdio, fd_obj.value)
    else:
        if int_ok:
            c_flags |= uv.INHERIT_STREAM
        uv.set_stdio_stream(stdio,
            cast(fd_obj,
                uv_stream.Stream, u".stdio[i].fd").stream)
    stdio.c_flags = rffi.cast(rffi.UINT, c_flags)

def _on_exit_(process, status, signal):
    ec = core.get_ec()
    self = ec.handles.get(process, Spawn)
    try:
        Event_dispatch(self.on_exit, [
            Integer(status),
            Integer(signal) ])
    except Unwinder as unwinder:
        core.root_unwind(unwinder)

@Spawn.method(u"kill", signature(Spawn, Integer))
def Spawn_kill(self, signum):
    check( uv.process_kill(self.process, signum.value) )
    return null

module.setattr_force(u"spawn", Spawn.interface)
