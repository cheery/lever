from space import *
from rpython.rlib import rfile
from rpython.rtyper.lltypesystem import rffi, lltype
import os
from runtime import pathobj

# TODO: https://msdn.microsoft.com/en-gb/library/windows/desktop/aa365198
#       http://man7.org/linux/man-pages/man7/aio.7.html

module = Module(u'fs', {}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

@builtin
def read_file(argv):
    if len(argv) < 1:
        raise Error(u"too few arguments to fs.read_file()")
    pathname = pathobj.to_path(argv[0])
    path = pathobj.os_stringify(pathname).encode('utf-8')
    convert = from_cstring
    if len(argv) > 1:
        for ch in as_cstring(argv[1]):
            if ch == 'b':
                convert = to_uint8array
            else:
                raise Error(u"unknown mode string action")
    try:
        fd = rfile.create_file(path, 'rb')
        try:
            return convert(fd.read())
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise Error(u"%s: %s" % (pathname.repr(), message))

@builtin
def open_(argv):
    if len(argv) < 1:
        raise Error(u"too few arguments to fs.open()")
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
        message = os.strerror(error.errno).decode('utf-8')
        raise Error(u"%s: %s" % (pathname.repr(), message))

class File(Object):
    def __init__(self, fd):
        self.fd = fd

@File.builtin_method
def read(argv):
    if len(argv) < 1:
        raise Error(u"too few arguments to file.read()")
    self = argv[0]
    if not isinstance(self, File):
        raise Error(u"expected file object")
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
