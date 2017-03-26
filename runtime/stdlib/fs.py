from rpython.rlib import rfile, rgc
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
import pathobj
from space import *
import os, sys
import errno

module = Module(u'fs', {}, frozen=True)

errorcode = Dict()
for num, name in errno.errorcode.items():
    errorcode.setitem(Integer(num), from_cstring(name))
    module.setattr_force(name.decode('utf-8'), Integer(num))
module.setattr_force(u"errorcode", errorcode)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

# TODO: consider what to do for .exists, .get*time, .read_file
@builtin
@signature(Object)
def exists(path):
    pathname = pathobj.to_path(path)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    return boolean(os.path.exists(path))

#@builtin
#@signature(Object)
#def stat(path):
#    pathname = pathobj.to_path(path)
#    path = pathobj.os_stringify(pathname).encode('utf-8')
#    try:
#        s = os.stat(path)
#    except IOError as error:
#        raise unwind(LIOError(pathname, error.errno))
#    res = Exnihilo()
#    for name, val in {
#        u"st_mode": Integer(s.st_mode),
#        u"st_ino": Integer(s.st_ino),
#        u"st_dev": Integer(s.st_dev),
#        u"st_nlink": Integer(s.st_nlink),
#        u"st_uid": Integer(s.st_uid),
#        u"st_gid": Integer(s.st_gid),
#        u"st_size": Integer(s.st_size),
#        u"st_atime": Float(s.st_atime),
#        u"st_mtime": Float(s.st_mtime),
#        u"st_ctime": Float(s.st_ctime)}.items():
#        res.setattr(name, val)
#    return res

@builtin
@signature(Object)
def getatime(path):
    pathname = pathobj.to_path(path)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        return Float(os.path.getatime(path))
    except IOError as error:
        raise unwind(LIOError(pathname, error.errno))

@builtin
@signature(Object)
def getmtime(path):
    pathname = pathobj.to_path(path)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        return Float(os.path.getmtime(path))
    except IOError as error:
        raise unwind(LIOError(pathname, error.errno))

@builtin
@signature(Object)
def getctime(path):
    pathname = pathobj.to_path(path)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        return Float(os.path.getctime(path))
    except IOError as error:
        raise unwind(LIOError(pathname, error.errno))

@builtin
def read_file(argv):
    if len(argv) < 1:
        raise OldError(u"too few arguments to fs.read_file()")
    pathname = pathobj.to_path(argv[0])
    path = pathobj.os_stringify(pathname).encode('utf-8')
    convert = from_cstring
    if len(argv) > 1:
        for ch in as_cstring(argv[1]):
            if ch == 'b':
                convert = to_uint8array
            else:
                raise OldError(u"unknown mode string action")
    try:
        fd = rfile.create_file(path, 'rb')
        try:
            return convert(fd.read())
        finally:
            fd.close()
    except IOError as error:
        raise unwind(LIOError(pathname, error.errno))

import rlibuv as uv
import uv_callback

for name, num in uv.file_flags.items():
    module.setattr_force(name, Integer(num))

@builtin
@signature(pathobj.Path, Integer, Integer, optional=1)
def open_(path, flags, mode):
    mode = 0664 if mode is None else mode.value
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_open(response.ec.uv_loop, req,
            path, flags.value, mode,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return File(rffi.r_long(req.c_result))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

class File(Object):
    def __init__(self, fd):
        self.fd = fd
        self.closed = False

@File.method(u"close", signature(File))
def File_close(self):
    self.closed = True
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_close(response.ec.uv_loop, req,
            self.fd,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@File.method(u"pread", signature(File, Object, Integer))
def File_pread(self, data, offset):
    bufs, nbufs = uv_callback.obj2bufs(data)
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_read(response.ec.uv_loop, req,
            self.fd, bufs, nbufs, offset.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return Integer(rffi.r_long(req.c_result))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(bufs, flavor='raw')
        lltype.free(req, flavor='raw')

@File.method(u"pwrite", signature(File, Object, Integer))
def File_pwrite(self, data, offset):
    bufs, nbufs = uv_callback.obj2bufs(data)
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_write(response.ec.uv_loop, req,
            self.fd, bufs, nbufs, offset.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return Integer(rffi.r_long(req.c_result))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(bufs, flavor='raw')
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path)
def unlink(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_unlink(response.ec.uv_loop, req,
            path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path, Integer, optional=1)
def mkdir(path, mode):
    mode = 0777 if mode is None else mode.value
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_mkdir(response.ec.uv_loop, req,
            path, mode,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path)
def mkdtemp(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    # TODO: XXXXXX  the last six characters must be these.
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_mkdtemp(response.ec.uv_loop, req,
            path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return from_cstring(rffi.charp2str(rffi.cast(rffi.CCHARP, req.c_path)))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path)
def rmdir(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_rmdir(response.ec.uv_loop, req,
            path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path)
def scandir(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    dirent = lltype.malloc(uv.dirent_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_scandir(response.ec.uv_loop, req,
            path, 0, # TODO: check if there are meaningful flags for this.
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        listing = []
        while True:
            res = uv.fs_scandir_next(req, dirent)
            if res == uv.EOF:
                break
            elif res < 0:
                raise uv_callback.to_error(res)
            entry = Exnihilo()
            entry.setattr(u"path",
                from_cstring(rffi.charp2str(dirent.c_name)))
            if dirent.c_type in uv.dirent2name:
                entry.setattr(u"type",
                    String(uv.dirent2name[dirent.c_type]))
            else:
                entry.setattr(u"type",
                    Integer(rffi.r_long(dirent.c_type)))
            listing.append(entry)
        return List(listing)
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(dirent, flavor='raw')
        lltype.free(req, flavor='raw')



@builtin
@signature(pathobj.Path)
def stat(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_stat(response.ec.uv_loop, req,
            path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return stat2data(req.c_statbuf)
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path)
def lstat(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_lstat(response.ec.uv_loop, req,
            path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return stat2data(req.c_statbuf)
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@File.method(u"stat", signature(File))
def File_stat(self):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_fstat(response.ec.uv_loop, req,
            self.fd,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return stat2data(req.c_statbuf)
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

def stat2data(s):
    res = Exnihilo()
    res.setattr(u"dev",       Integer(rffi.r_long(s.c_st_dev)))
    res.setattr(u"mode",      Integer(rffi.r_long(s.c_st_mode)))
    res.setattr(u"nlink",     Integer(rffi.r_long(s.c_st_nlink)))
    res.setattr(u"uid",       Integer(rffi.r_long(s.c_st_uid)))
    res.setattr(u"gid",       Integer(rffi.r_long(s.c_st_gid)))
    res.setattr(u"rdev",      Integer(rffi.r_long(s.c_st_rdev)))
    res.setattr(u"ino",       Integer(rffi.r_long(s.c_st_ino)))
    res.setattr(u"size",      Integer(rffi.r_long(s.c_st_size)))
    res.setattr(u"blksize",   Integer(rffi.r_long(s.c_st_blksize)))
    res.setattr(u"blocks",    Integer(rffi.r_long(s.c_st_blocks)))
    res.setattr(u"flags",     Integer(rffi.r_long(s.c_st_flags)))
    res.setattr(u"gen",       Integer(rffi.r_long(s.c_st_gen)))
    res.setattr(u"atime",     timespec2number(s.c_st_atim))
    res.setattr(u"mtime",     timespec2number(s.c_st_mtim))
    res.setattr(u"ctime",     timespec2number(s.c_st_ctim))
    res.setattr(u"birthtime", timespec2number(s.c_st_birthtim))
    return res

def timespec2number(ts):
    return Float(ts.c_tv_sec + ts.c_tv_nsec * 10e-9)

@builtin
@signature(pathobj.Path, pathobj.Path)
def rename(path, new_path):
    path = pathobj.os_stringify(path).encode('utf-8')
    new_path = pathobj.os_stringify(new_path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_rename(response.ec.uv_loop, req,
            path, new_path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@File.method(u"sync", signature(File))
def File_fsync(self):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_fsync(response.ec.uv_loop, req,
            self.fd,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@File.method(u"datasync", signature(File))
def File_fdatasync(self):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_fdatasync(response.ec.uv_loop, req,
            self.fd,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')


@File.method(u"truncate", signature(File, Integer))
def File_truncate(self, offset):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_ftruncate(response.ec.uv_loop, req,
            self.fd, offset.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(File, File, Integer, Integer)
def sendfile(out_file, in_file, in_offset, length):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_sendfile(response.ec.uv_loop, req,
            out_file.fd, in_file.fd, in_offset.value, length.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return Integer(rffi.r_long(req.c_result))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path, Integer)
def access(path, mode):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_access(response.ec.uv_loop, req,
            path, mode.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path, Integer)
def chmod(path, mode):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_chmod(response.ec.uv_loop, req,
            path, mode.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@File.method(u"chmod", signature(File, Integer))
def File_chmod(self, mode):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_fchmod(response.ec.uv_loop, req,
            self.fd, mode.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path, Float, Float)
def utime(path, atime, mtime):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_utime(response.ec.uv_loop, req,
            path, atime.number, mtime.number,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@File.method(u"utime", signature(File, Float, Float))
def File_utime(self, atime, mtime):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_futime(response.ec.uv_loop, req,
            self.fd, atime.number, mtime.number,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path, pathobj.Path)
def link(path, new_path):
    path = pathobj.os_stringify(path).encode('utf-8')
    new_path = pathobj.os_stringify(new_path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_link(response.ec.uv_loop, req,
            path, new_path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path, pathobj.Path)
def symlink(path, new_path):
    path = pathobj.os_stringify(path).encode('utf-8')
    new_path = pathobj.os_stringify(new_path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_symlink(response.ec.uv_loop, req,
            path, new_path, 0, # TODO: FS_SYMLINK_DIR, FS_SYMLINK_JUNCTION -flags.
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path)
def readlink(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_readlink(response.ec.uv_loop, req,
            path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        # hmm?
        return from_cstring(rffi.charp2str(rffi.cast(rffi.CCHARP, req.c_ptr)))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path)
def realpath(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_realpath(response.ec.uv_loop, req,
            path,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        # hmm?
        return from_cstring(rffi.charp2str(rffi.cast(rffi.CCHARP, req.c_ptr)))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@builtin
@signature(pathobj.Path, Integer, Integer)
def chown(path, uid, gid):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_chown(response.ec.uv_loop, req,
            path, uid.value, gid.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

@File.method(u"chown", signature(File, Integer, Integer))
def File_chown(self, uid, gid):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_fchown(response.ec.uv_loop, req,
            self.fd, uid.value, gid.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')

import core
from uv_handle import Handle, check, Handle_close
import uv_handle
 
class Watch(Handle):
    def __init__(self, fs_event):
        Handle.__init__(self, rffi.cast(uv.handle_ptr, fs_event))
        self.fs_event = fs_event
        self.data = []
        self.status = 0
        self.greenlet = None
    
    def iter(self):
        return self

@Watch.instantiator2(signature(pathobj.Path))
def Watch_init(path):
    ec = core.get_ec()
    path = pathobj.os_stringify(path).encode('utf-8')

    handle = lltype.malloc(uv.fs_event_ptr.TO, flavor='raw', zero=True)
    res = uv.fs_event_init(ec.uv_loop, handle)
    if res < 0:
        lltype.free(handle, flavor='raw')
        raise uv_callback.to_error(res)
    self = Watch(handle)
    uv_callback.push(ec.uv__fs_event, self)
    
    res = uv.fs_event_start(self.fs_event, _fs_event_cb_, path, 0)
    if res < 0:
        uv_callback.drop(ec.uv__fs_event, self.fs_event)
        Handle_close(self)
        raise uv_callback.to_error(res)
    return self

def _fs_event_cb_(handle, filename, events, status):
    ec = core.get_ec()
    try:
        self = uv_callback.peek(ec.uv__fs_event, handle)
        status = rffi.r_long(status)
        if self.status == 0 and status < 0:
            uv_callback.drop(ec.uv__fs_event, handle)
            self.status = status
            return
        obj = Exnihilo()
        obj.setattr(u"path", from_cstring(rffi.charp2str(filename)))
        if rffi.r_long(events) == 1:
            obj.setattr(u"type", String(u"rename"))
        else:
            obj.setattr(u"type", String(u"change"))
        if self.greenlet is None:
            self.data.append(obj)
        else:
            greenlet, self.greenlet = self.greenlet, None
            core.switch([greenlet, obj])
    except Unwinder as unwinder:
        core.root_unwind(ec, unwinder)
 
# Not needed because the .close will signal ECANCELED to
# the callback.
#@Watch.method(u"close", signature(Watch))
#def Watch_close(self):
#    ec = core.get_ec()
#    check( uv.fs_event_stop(ec.uv_loop, self.fs_event) )
#    self.status = uv.EOF
#    return Handle_close(self)

@Watch.method(u"next", signature(Watch))
def Watch_next(self):
    if len(self.data) > 0:
        return self.data.pop(0)
    elif self.status == uv.EOF or self.status == uv.ECANCELED:
        raise StopIteration()
    elif self.status < 0:
        raise uv_callback.to_error(self.status)
    else:
        if self.greenlet is not None:
            raise unwind(LError(u"fs.watch retrieval collision"))
        ec = core.get_ec()
        self.greenlet = ec.current
        return core.switch([ec.eventloop])

@Watch.method(u"wait", signature(Watch))
def Watch_wait(self):
    if len(self.data) > 0:
        return self.data.pop(0)
    elif self.status < 0:
        raise uv_callback.to_error(self.status)
    else:
        if self.greenlet is not None:
            raise unwind(LError(u"fs.watch retrieval collision"))
        ec = core.get_ec()
        self.greenlet = ec.current
        return core.switch([ec.eventloop])

class FileStream(Object):
    def __init__(self, fileobj, offset):
        self.fileobj = fileobj
        self.offset = offset

    def getattr(self, name):
        if name == u"file":
            return self.fileobj
        elif name == u"offset":
            return Integer(self.offset)
        else:
            return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"offset":
            self.offset = cast(value, Integer, u"FileStream.offset").value
            return value
        else:
            return Object.setattr(self, name, value)

@FileStream.method(u"close", signature(FileStream))
def FileStream_close(self):
    return File_close(self.fileobj)

class ReadStream(FileStream):
    pass

@ReadStream.instantiator2(signature(File, Integer, optional=1))
def ReadStream_init(fileobj, offset):
    offset = 0 if offset is None else offset.value
    return ReadStream(fileobj, offset)

@ReadStream.method(u"read", signature(ReadStream))
def ReadStream_read(self):
    data = alloc_uint8array(64*1024)
    count = File_pread(self.fileobj, data, Integer(self.offset))
    self.offset += count.value
    if count.value == 0:
        raise uv_callback.to_error(uv.EOF)
    return data.subslice(count.value)

class WriteStream(FileStream):
    pass

@WriteStream.instantiator2(signature(File, Integer, optional=1))
def WriteStream_init(fileobj, offset):
    offset = 0 if offset is None else offset.value
    return WriteStream(fileobj, offset)

@WriteStream.method(u"write", signature(WriteStream, Object))
def WriteStream_write(self, data):
    count = File_pwrite(self.fileobj, data, Integer(self.offset))
    self.offset += count.value
    return null

module.setattr_force(u"watch", Watch.interface)
module.setattr_force(u"File", File.interface)
module.setattr_force(u"ReadStream",  ReadStream.interface)
module.setattr_force(u"WriteStream", WriteStream.interface)

