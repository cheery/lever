from rpython.rlib.rstruct import ieee
from rpython.rlib import rfile
from bon import open_file
from space import *
import pathobj, os

def write_file(pathname, data):
    name = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        fd = rfile.create_file(name, "wb")
        try:
            dump(fd, data)
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise OldError(u"%s: %s" % (pathobj.stringify(pathname), message))
    return null

def dump(fd, data):
    tp = get_interface(data)
    if tp is Integer.interface:
        fd.write(chr(0))
        wlong(fd, data)
    elif tp is Float.interface:
        fd.write(chr(1))
        wdouble(fd, data)
    elif tp is String.interface:
        fd.write(chr(2))
        wstring(fd, data)
    elif tp is List.interface:
        fd.write(chr(3))
        wlist(fd, data)
    elif tp is Dict.interface:
        fd.write(chr(4))
        wdict(fd, data)
    elif tp is Uint8Array.interface:
        fd.write(chr(5))
        wbytes(fd, data)
    elif tp is Boolean.interface:
        fd.write(chr(6))
        wboolean(fd, data)
    elif tp is null:
        fd.write(chr(7))
    else:
        raise OldError(u"no binon encoding found for an object.")

def w32(fd, value):
    fd.write(''.join([
        chr(value >> 24 & 255),
        chr(value >> 16 & 255),
        chr(value >> 8 & 255),
        chr(value >> 0 & 255),
    ]))

def wlong(fd, num):
    "http://en.wikipedia.org/wiki/Variable-length_quantity"
    assert isinstance(num, Integer)
    value = num.value
    output = []
    if value < 0:
        negative = True
        value = -value
    else:
        negative = False
    output.append(value & 0x7F)
    while value > 0x7F:
        value >>= 7
        output.append(0x80 | value & 0x7F)
    if output[-1] & 0x40 != 0:
        output.append(0x80)
    if negative:
        output[-1] |= 0x40
    result = []
    for x in reversed(output):
        result.append(chr(x))
    fd.write(''.join(result))

def wdouble(fd, obj):
    assert isinstance(obj, Float)
    result = []
    ieee.pack_float(result, obj.number, 8, True)
    fd.write(''.join(result))

def wstring(fd, obj):
    assert isinstance(obj, String)
    s = obj.string.encode('utf-8')
    w32(fd, len(s))
    fd.write(s)

def wlist(fd, obj):
    assert isinstance(obj, List)
    w32(fd, len(obj.contents))
    for o in obj.contents:
        dump(fd, o)

def wdict(fd, obj):
    assert isinstance(obj, Dict)
    w32(fd, len(obj.data))
    for key, value in obj.data.items():
        dump(fd, key)
        dump(fd, value)

def wbytes(fd, obj):
    assert isinstance(obj, Uint8Data)
    w32(fd, obj.length)
    result = []
    for i in range(obj.length):
        result.append(chr(obj.uint8data[i]))
    fd.write(''.join(result))

def wboolean(fd, obj):
    if is_true(obj):
        return fd.write('\x01')
    else:
        return fd.write('\x00')

def wnull(fd, obj):
    pass

module = Module(u'binon', {
    u"read_file": Builtin(
        signature(Object)(open_file),
        u"read_file"),
    u"write_file": Builtin(
        signature(Object, Object)(write_file),
        u"write_file"),
}, frozen=True)
