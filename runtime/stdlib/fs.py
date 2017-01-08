from rpython.rlib import rfile
from rpython.rtyper.lltypesystem import rffi, lltype
import pathobj
from space import *
import os
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

@builtin
@signature(Object)
def exists(path):
    pathname = pathobj.to_path(path)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    return boolean(os.path.exists(path))

@builtin
@signature(Object)
def stat(path):
    pathname = pathobj.to_path(path)
    path = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        s = os.stat(path)
    except IOError as error:
        raise unwind(LIOError(pathname, error.errno))
    res = Exnihilo()
    for name, val in {
        u"st_mode": Integer(s.st_mode),
        u"st_ino": Integer(s.st_ino),
        u"st_dev": Integer(s.st_dev),
        u"st_nlink": Integer(s.st_nlink),
        u"st_uid": Integer(s.st_uid),
        u"st_gid": Integer(s.st_gid),
        u"st_size": Integer(s.st_size),
        u"st_atime": Float(s.st_atime),
        u"st_mtime": Float(s.st_mtime),
        u"st_ctime": Float(s.st_ctime)}.items():
        res.setattr(name, val)
    return res

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

@builtin
def open_(argv):
    if len(argv) < 1:
        raise OldError(u"too few arguments to fs.open()")
    pathname = pathobj.to_path(argv[0])
    path = pathobj.os_stringify(pathname).encode('utf-8')
    if len(argv) > 1:
        mode = as_cstring(argv[1])
        mode += 'b'
    else:
        mode = 'rb'
    try:
        return File(rfile.create_file(path, 'rb'))
    except IOError as error:
        raise unwind(LIOError(pathname, error.errno))

class File(Object):
    def __init__(self, fd):
        self.fd = fd

@File.builtin_method
def read(argv):
    if len(argv) < 1:
        raise OldError(u"too few arguments to file.read()")
    self = argv[0]
    if not isinstance(self, File):
        raise OldError(u"expected file object")
    if len(argv) > 1:
        count_or_dst = argv[1]
        if isinstance(count_or_dst, Uint8Array):
            dst = count_or_dst
            data = rffi.cast(rffi.CCHARP, dst.uint8data)
            count = rfile.c_fread(data, 1, dst.length, self.fd._ll_file)
            return Integer(rffi.r_long(count))
        else:
            count = to_int(count_or_dst)
            return to_uint8array(self.fd.read(int(count)))
    else:
        return to_uint8array(self.fd.read())

@File.builtin_method
@signature(File, Uint8Array)
def write(self, src):
    data = rffi.cast(rffi.CCHARP, src.uint8data)
    count = rfile.c_fwrite(data, 1, src.length, self.fd._ll_file)
    return Integer(rffi.r_long(count))

@File.builtin_method
@signature(File)
def close(self):
    self.fd.close()
    return null

@File.builtin_method
@signature(File, Object)
def seek(self, pos):
    self.fd.seek(to_int(pos))
    return null

@File.builtin_method
@signature(File)
def tell(self):
    return Integer(self.fd.tell())

@File.builtin_method
@signature(File, Object)
def truncate(self, pos):
    return self.fd.truncate(to_int(pos))

@File.builtin_method
@signature(File)
def fileno(self):
    return Integer(rffi.r_long(self.fd.fileno()))

@File.builtin_method
@signature(File)
def isatty(self):
    return boolean(self.fd.fileno())

@File.builtin_method
@signature(File)
def flush(self):
    self.fd.flush()
    return null

module.setattr_force(u"file", File.interface)

from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
import rlibuv as uv
import uv_callback


# void uv_fs_req_cleanup(uv_fs_t* req)
# int uv_fs_close(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)
# int uv_fs_open(uv_loop_t* loop, uv_fs_t* req, const char* path, int flags, int mode, uv_fs_cb cb)
# int uv_fs_read(uv_loop_t* loop, uv_fs_t* req, uv_file file, const uv_buf_t bufs[], unsigned int nbufs, int64_t offset, uv_fs_cb cb)
# int uv_fs_unlink(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb)
# int uv_fs_write(uv_loop_t* loop, uv_fs_t* req, uv_file file, const uv_buf_t bufs[], unsigned int nbufs, int64_t offset, uv_fs_cb cb)

@builtin
@signature(pathobj.Path)
def mkdir(path):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_mkdir(response.ec.uv_loop, req,
            path, 0777,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return null
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')
# int uv_fs_mkdir(uv_loop_t* loop, uv_fs_t* req, const char* path, int mode, uv_fs_cb cb)

# int uv_fs_mkdtemp(uv_loop_t* loop, uv_fs_t* req, const char* tpl, uv_fs_cb cb)
# XXXXXX  the last six characters must be these.
# result given in req.path
# it can be expected to be removed after that.

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
# int uv_fs_rmdir(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb)

# int uv_fs_scandir(uv_loop_t* loop, uv_fs_t* req, const char* path, int flags, uv_fs_cb cb)
# int uv_fs_scandir_next(uv_fs_t* req, uv_dirent_t* ent)
# int uv_fs_stat(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb)
# int uv_fs_fstat(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)
# int uv_fs_lstat(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb)
# int uv_fs_rename(uv_loop_t* loop, uv_fs_t* req, const char* path, const char* new_path, uv_fs_cb cb)
# int uv_fs_fsync(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)
# int uv_fs_fdatasync(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)
# int uv_fs_ftruncate(uv_loop_t* loop, uv_fs_t* req, uv_file file, int64_t offset, uv_fs_cb cb)
# int uv_fs_sendfile(uv_loop_t* loop, uv_fs_t* req, uv_file out_fd, uv_file in_fd, int64_t in_offset, size_t length, uv_fs_cb cb)
# int uv_fs_access(uv_loop_t* loop, uv_fs_t* req, const char* path, int mode, uv_fs_cb cb)
# int uv_fs_chmod(uv_loop_t* loop, uv_fs_t* req, const char* path, int mode, uv_fs_cb cb)
# int uv_fs_fchmod(uv_loop_t* loop, uv_fs_t* req, uv_file file, int mode, uv_fs_cb cb)
# int uv_fs_utime(uv_loop_t* loop, uv_fs_t* req, const char* path, double atime, double mtime, uv_fs_cb cb)
# int uv_fs_futime(uv_loop_t* loop, uv_fs_t* req, uv_file file, double atime, double mtime, uv_fs_cb cb)
# int uv_fs_link(uv_loop_t* loop, uv_fs_t* req, const char* path, const char* new_path, uv_fs_cb cb)
# int uv_fs_symlink(uv_loop_t* loop, uv_fs_t* req, const char* path, const char* new_path, int flags, uv_fs_cb cb)
# int uv_fs_readlink(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_fs_cb cb)
# int uv_fs_chown(uv_loop_t* loop, uv_fs_t* req, const char* path, uv_uid_t uid, uv_gid_t gid, uv_fs_cb cb)
# int uv_fs_fchown(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_uid_t uid, uv_gid_t gid, uv_fs_cb cb)
