from space import *
from rpython.rlib import rfile
import os

class Stream(object):
    def __init__(self, data, index=0):
        self.data = data
        self.index = index

    def read(self, count):
        if self.index + count > len(self.data):
            raise Error(u"Read error: End of file")
        data = self.data[self.index:self.index+count]
        self.index += count
        return data

    def read_ubyte(self):
        return ord(self.read(1))

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
        return self.read(self.read_integer()).decode('utf-8')

def open_file(pathname):
    try:
        fd = rfile.create_file(as_cstring(pathname), 'r')
        try:
            return Stream(fd.read())
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise Error(u"%s: %s" % (pathname.string, message))
