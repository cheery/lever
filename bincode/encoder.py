"""
    This part of the code likely won't compile by RPython.
"""
import common
from collections import OrderedDict

class Function(object):
    def __init__(self, flags, argc, localc, blocks, functions):
        self.flags = flags
        self.argc = argc
        self.localc = localc
        self.blocks = blocks
        self.functions = functions

    def dump(self, stream):
        stream.write_integer(self.flags)
        stream.write_integer(self.argc)
        stream.write_integer(self.localc)
        stream.write_integer(len(self.blocks))
        for block in self.blocks:
            stream.write_integer(len(block))
            stream.write(block)
        stream.write_integer(len(self.functions))
        for func in self.functions:
            func.dump(stream)

class StringTable(object):
    def __init__(self):
        self.strings = OrderedDict()

    def get(self, string):
        string_table = self.strings
        if string in string_table:
            return string_table[string]
        string_table[string] = len(string_table)
        return string_table[string]

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

def open_file(pathname):
    return WriteStream(open(pathname, 'w'))

def dump_function(pathname, entry, strtab):
    stream = open_file(pathname)
    stream.write(common.header)
    entry.dump(stream)
    # write string table
    stream.write_integer(len(strtab.strings))
    for string in strtab.strings:
        stream.write_string(string)
    stream.close()
