"""
    binary object notation

    A data-interchange format. Used here because it is simpler to
    decode than other similar formats and can contain custom encodings.
"""
from space import *
from rpython.rlib import rfile
from rpython.rlib.rstruct import ieee
from rpython.rtyper.lltypesystem import rffi
from runtime import pathobj
import os

#types = {}
decoder = {}
#encoder = {} todo?

def open_file(pathname):
    name = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        fd = rfile.create_file(name, 'rb')
        try:
            return load(fd)
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise OldError(u"%s: %s" % (pathobj.stringify(pathname), message))

def load(fd):
    type_id = ord(fd.read(1)[0])
    return decoder[type_id](fd)

def r32(fd):
    a, b, c, d = fd.read(4)
    return ord(a) << 24 | ord(b) << 16 | ord(c) << 8 | ord(d)

def rlong(fd):
    "http://en.wikipedia.org/wiki/Variable-length_quantity"
    # Slightly broken, doesn't handle integer overflow.
    sign = +1
    output = 0
    ubyte = ord(fd.read(1)[0])
    if ubyte & 0x40 == 0x40:
        sign = -1
        ubyte &= 0xBF
    while ubyte & 0x80:
        output |= ubyte & 0x7F
        output <<= 7
        ubyte = ord(fd.read(1)[0])
    output |= ubyte
    return Integer(rffi.r_long(output * sign))

decoder[0] = rlong

def rdouble(fd):
    data = fd.read(8)
    return Float(ieee.unpack_float(data, True))

decoder[1] = rdouble

def rstring(fd):
    length = r32(fd)
    return String(fd.read(length).decode('utf-8'))

decoder[2] = rstring

def rlist(fd):
    length = r32(fd)
    sequence = []
    for _ in range(length):
        sequence.append(load(fd))
    return List(sequence)

decoder[3] = rlist

def rdict(fd):
    length = r32(fd)
    dictionary = Dict()
    for _ in range(length):
        key = load(fd)
        val = load(fd)
        dictionary.setitem(key, val)
    return dictionary

decoder[4] = rdict

def rbytes(fd):
    length = r32(fd)
    return to_uint8array(fd.read(length))

decoder[5] = rbytes

def rboolean(fd):
    if fd.read(1)[0] == '\x00':
        return true
    else:
        return false

decoder[6] = rboolean

def rnull(fd):
    return null

decoder[7] = rnull
