from rpython.rlib import rfile, rgc
from rpython.rtyper.lltypesystem import rffi, lltype
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

# TODO: consider what to do for these.
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

for name, num in uv.file_flags.items():
    module.setattr_force(name, Integer(num))

# void uv_fs_req_cleanup(uv_fs_t* req)

@builtin
@signature(pathobj.Path, Integer, Integer)
def raw_open(path, flags, mode):
    path = pathobj.os_stringify(path).encode('utf-8')
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_open(response.ec.uv_loop, req,
            path, flags.value, mode.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return Integer(rffi.r_long(req.c_result))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')
# int uv_fs_open(uv_loop_t* loop, uv_fs_t* req, const char* path, int flags, int mode, uv_fs_cb cb)

@builtin
@signature(Integer)
def raw_close(fileno):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_close(response.ec.uv_loop, req,
            fileno.value,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return Integer(rffi.r_long(req.c_result))
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')
# int uv_fs_close(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)

@builtin
@signature(Integer, List, Integer)
def raw_read(fileno, arrays, offset):
    L = len(arrays.contents)
    bufs = lltype.malloc(rffi.CArray(uv.buf_t), L, flavor='raw', zero=True)
    try:
        i = 0
        for obj in arrays.contents:
            obj = cast(obj, Uint8Array, u"raw_read expects uint8arrays")
            bufs[i].c_base = rffi.cast(rffi.CCHARP, obj.uint8data)
            bufs[i].c_len = rffi.r_size_t(obj.length)
            i += 1
        return Integer(rffi.r_long(fs_read(
            fileno.value, bufs, L, offset.value)))
    finally:
        lltype.free(bufs, flavor='raw')

def fs_read(fileno, bufs, nbufs, offset):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_read(response.ec.uv_loop, req,
            fileno, bufs, nbufs, offset,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return req.c_result
    finally:
        uv.fs_req_cleanup(req)
        lltype.free(req, flavor='raw')


@builtin
@signature(Integer, List, Integer)
def raw_write(fileno, arrays, offset):
    L = len(arrays.contents)
    bufs = lltype.malloc(rffi.CArray(uv.buf_t), L, flavor='raw', zero=True)
    try:
        i = 0
        for obj in arrays.contents:
            obj = cast(obj, Uint8Array, u"raw_write expects uint8arrays")
            bufs[i].c_base = rffi.cast(rffi.CCHARP, obj.uint8data)
            bufs[i].c_len = rffi.r_size_t(obj.length)
            i += 1
        return Integer(rffi.r_long(fs_write(
            fileno.value, bufs, L, offset.value)))
    finally:
        lltype.free(bufs, flavor='raw')

def fs_write(fileno, bufs, nbufs, offset):
    req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
    try:
        response = uv_callback.fs(req)
        response.wait(uv.fs_write(response.ec.uv_loop, req,
            fileno, bufs, nbufs, offset,
            uv_callback.fs.cb))
        if req.c_result < 0:
            raise uv_callback.to_error(req.c_result)
        return req.c_result
    finally:
        uv.fs_req_cleanup(req)
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
@signature(pathobj.Path, Integer, optional=1) # TODO: add mode as an option.
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
        response.wait(uv.fs_readlink(response.ec.uv_loop, req,
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

# int uv_fs_fstat(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)

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

# int uv_fs_fsync(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)
# int uv_fs_fdatasync(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_fs_cb cb)
# int uv_fs_ftruncate(uv_loop_t* loop, uv_fs_t* req, uv_file file, int64_t offset, uv_fs_cb cb)
# int uv_fs_sendfile(uv_loop_t* loop, uv_fs_t* req, uv_file out_fd, uv_file in_fd, int64_t in_offset, size_t length, uv_fs_cb cb)

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
# int uv_fs_fchmod(uv_loop_t* loop, uv_fs_t* req, uv_file file, int mode, uv_fs_cb cb)

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
# int uv_fs_futime(uv_loop_t* loop, uv_fs_t* req, uv_file file, double atime, double mtime, uv_fs_cb cb)

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

# int uv_fs_fchown(uv_loop_t* loop, uv_fs_t* req, uv_file file, uv_uid_t uid, uv_gid_t gid, uv_fs_cb cb)
