"""
    This part of the code likely won't compile by RPython.
"""
import common
import struct
from collections import OrderedDict

class Function(object):
    def __init__(self, flags, tmpc, argc, localc, blocks, functions):
        self.flags = flags
        self.tmpc = tmpc
        self.argc = argc
        self.localc = localc
        self.blocks = blocks
        self.functions = functions

    def dump(self, stream):
        stream.write_integer(self.flags)
        stream.write_integer(self.tmpc)
        stream.write_integer(self.argc)
        stream.write_integer(self.localc)
        stream.write_integer(len(self.blocks))
        for block in self.blocks:
            stream.write_integer(len(block))
            stream.write(block)
        stream.write_integer(len(self.functions))
        for func in self.functions:
            func.dump(stream)

class ConstantTable(object):
    def __init__(self):
        self.constants = OrderedDict()

    def get(self, const):
        const_table = self.constants
        if const in const_table:
            return const_table[const]
        const_table[const] = len(const_table)
        return const_table[const]

class WriteStream(object):
    def __init__(self, fd):
        self.fd = fd

    def close(self):
        self.fd.close()

    def write(self, data):
        self.fd.write(data)

    def write_ubyte(self, ubyte):
        return self.write(chr(ubyte))

    def write_uint(self, uint):
        self.write_ubyte(uint >> 0  & 0xFF)
        self.write_ubyte(uint >> 8  & 0xFF)
        self.write_ubyte(uint >> 16 & 0xFF)
        self.write_ubyte(uint >> 24 & 0xFF)

    def write_integer(self, value):
        "http://en.wikipedia.org/wiki/Variable-length_quantity"
        output = []
        output.append(value & 0x7F)
        while value > 0x7F:
            value >>= 7
            output.append(0x80 | value & 0x7F)
        self.write(''.join(map(chr, reversed(output))))

    def write_string(self, string):
        data = string.encode('utf-8')
        self.write_integer(len(data))
        self.write(data)

    def write_i64(self, value):
        self.write(struct.pack('l', value))

    def write_double(self, value):
        self.write(struct.pack('d', value))

def open_file(pathname):
    return WriteStream(open(pathname, 'w'))

def dump_function(pathname, entry, consttab):
    stream = open_file(pathname)
    stream.write(common.header)
    entry.dump(stream)
    # write string table
    stream.write_integer(len(consttab.constants))
    for const in consttab.constants:
        if isinstance(const, (str, unicode)):
            stream.write_ubyte(0x01)
            stream.write_string(const)
        elif isinstance(const, (int, long)):
            stream.write_ubyte(0x02)
            stream.write_i64(const)
        elif isinstance(const, float):
            stream.write_ubyte(0x03)
            stream.write_float(const)
        else:
            assert False, "insert encoding for constant"
    stream.close()
