from space import *
from rpython.rlib import rfile
from rpython.rlib.rstruct import ieee
from rpython.rtyper.lltypesystem import rffi
import os
import struct

class Stream(object):
    def __init__(self, data, index=0):
        self.data = data
        assert index >= 0
        self.index = index

    def read(self, count):
        assert count >= 0
        if self.index + count > len(self.data):
            raise Error(u"Read error: End of file")
        data = self.data[self.index:self.index+count]
        self.index += count
        return data

    def read_ubyte(self):
        return ord(self.read(1)[0])

    def read_uint(self):
        return (self.read_ubyte() << 0 |
                self.read_ubyte() << 8 |
                self.read_ubyte() << 16 |
                self.read_ubyte() << 24)

    def read_integer(self):
        "http://en.wikipedia.org/wiki/Variable-length_quantity"
        output = 0
        ubyte = self.read_ubyte()
        while ubyte & 0x80:
            output |= ubyte & 0x7F
            output <<= 7
            ubyte = self.read_ubyte()
        output |= ubyte
        return output

    def read_string(self):
        return self.read(self.read_u16()).decode('utf-8')

    def read_double(self):
        data = self.read(8)
        return ieee.unpack_float(data, False)

    def read_u16(self):
        return (self.read_ubyte() << 0 |
                self.read_ubyte() << 8)

    def read_u64(self):
        return rffi.r_ulong(self.read_uint() << 0 | self.read_uint() << 32)

    def read_i64(self):
        assert rffi.sizeof(rffi.LONG) == 8
        return rffi.cast(rffi.LONG, self.read_u64())

sign_mask = 1L << 63

def open_file(pathname):
    try:
        fd = rfile.create_file(pathname, 'rb')
        try:
            return Stream(fd.read())
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise Error(u"%s: %s" % (pathname.decode('utf-8'), message))
