"""
    binary object notation

    A data-interchange format. Used here because it is simpler to
    decode than other similar formats and can contain custom encodings.
"""
import struct

types = {}
decoder = {}
encoder = {}

def load(fd):
    type_id = ord(fd.read(1))
    return decoder[type_id](fd)

def dump(fd, obj):
    type_id = types[type(obj)]
    fd.write(chr(type_id))
    return encoder[type_id](fd, obj)

def r32(fd):
    a, b, c, d = fd.read(4)
    return ord(a) << 24 | ord(b) << 16 | ord(c) << 8 | ord(d)

def w32(fd, value):
    fd.write(''.join((
        chr(value >> 24 & 255),
        chr(value >> 16 & 255),
        chr(value >> 8 & 255),
        chr(value >> 0 & 255),
    )))

def rlong(fd):
    "http://en.wikipedia.org/wiki/Variable-length_quantity"
    sign = +1
    output = 0
    ubyte = ord(fd.read(1))
    if ubyte & 0x40 == 0x40:
        sign = -1
        ubyte &= 0xBF
    while ubyte & 0x80:
        output |= ubyte & 0x7F
        output <<= 7
        ubyte = ord(fd.read(1))
    output |= ubyte
    return output * sign

def wlong(fd, value):
    "http://en.wikipedia.org/wiki/Variable-length_quantity"
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
    fd.write(''.join(map(chr, reversed(output))))

types[int] = 0
types[long] = 0
decoder[0] = rlong
encoder[0] = wlong

def rdouble(fd):
    return struct.unpack('!d', fd.read(8))[0]

def wdouble(fd, obj):
    fd.write(struct.pack('!d', obj))

types[float] = 1
decoder[1] = rdouble
encoder[1] = wdouble

def rstring(fd):
    length = r32(fd)
    return fd.read(length).decode('utf-8')

def wstring(fd, obj):
    w32(fd, len(obj))
    fd.write(obj.encode('utf-8'))

types[unicode] = 2
decoder[2] = rstring
encoder[2] = wstring

def rlist(fd):
    length = r32(fd)
    sequence = []
    for _ in range(length):
        sequence.append(load(fd))
    return sequence

def wlist(fd, obj):
    w32(fd, len(obj))
    for value in obj:
        dump(fd, value)

types[list] = 3
types[tuple] = 3
decoder[3] = rlist
encoder[3] = wlist

def rdict(fd):
    length = r32(fd)
    dictionary = dict()
    for _ in range(length):
        key = load(fd)
        val = load(fd)
        dictionary[key] = val
    return dictionary

def wdict(fd, obj):
    w32(fd, len(obj))
    for key, value in obj.iteritems():
        dump(fd, key)
        dump(fd, value)

types[dict] = 4
decoder[4] = rdict
encoder[4] = wdict

def rbytes(fd):
    length = r32(fd)
    return fd.read(length)

def wbytes(fd, obj):
    w32(fd, len(obj))
    fd.write(obj)

types[bytes] = 5
decoder[5] = rbytes
encoder[5] = wbytes

def rboolean(fd):
    return fd.read(1) != '\x00'

def wboolean(fd, obj):
    return fd.write('\x00\x01'[obj])

types[bool] = 6
decoder[6] = rboolean
encoder[6] = wboolean

def rnull(fd):
    return None

def wnull(fd, obj):
    pass

types[type(None)] = 7
decoder[7] = rnull
encoder[7] = wnull
