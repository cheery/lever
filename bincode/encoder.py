"""
    This part of the code likely won't compile by RPython.
"""

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
