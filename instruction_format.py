from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize

# I may change this significantly later.

def enc_code(name, *args):
    assert len(args) < 16
    return enc_vlq(opcode(name) | len(args)) + ''.join(map(enc_vlq, args))

# arguments are tagged with types.
ARG_LOCAL, ARG_RAW, ARG_CONST, ARG_BLOCK = range(4)
ARG_SHIFT = 2

@jit.unroll_safe
def dec_code(data, pc):
    op, pc = dec_vlq(data, pc)
    arity = op & 15
    opcode = op & ~15
    args = []
    for i in range(arity):
        val, pc = dec_vlq(data, pc)
        args.append(val)
    return pc, opcode, args

def enc_vlq(value):
    "http://en.wikipedia.org/wiki/Variable-length_quantity"
    output = []
    output.append(value & 0x7F)
    while value > 0x7F:
        value >>= 7
        output.append(0x80 | value & 0x7F)
    return ''.join(map(chr, reversed(output)))

def dec_vlq(data, index):
    "http://en.wikipedia.org/wiki/Variable-length_quantity"
    output = 0
    while ord(data[index]) & 0x80:
        output |= ord(data[index]) & 0x7F
        output <<= 7
        index += 1
    output |= ord(data[index])
    index += 1
    return output, index

# Using a table and non-vlq to represent opcode value would be more
# memory efficient, but I wanted instructions that can be decoded without
# a table, for experimenting with things.
@specialize.memo()
def opcode(name):
    assert len(name) <= 4
    value = 0
    for ch in name:
        code = ord(ch.lower())
        assert ord('a') <= code <= ord('z')
        value = value << 5 | (code - ord('a') + 1) & 31
    return value << 5

# This would be pointless when interpreting, it's here separately.
def opname(value):
    value = value >> 5
    name = []
    while value > 0:
        name.append(chr((value & 31) + ord('a') - 1))
        value >>= 5
    name.reverse()
    return ''.join(name)
