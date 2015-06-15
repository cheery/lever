from space import *
import bincode.common
import bincode.decoder
from instruction_format import dec_code, opname

class Function(object):
    def __init__(self, strtab, flags, argc, localc, blocks, functions):
        self.strtab = strtab
        self.flags = flags
        self.argc = argc
        self.localc = localc
        self.blocks = blocks
        self.functions = functions

    def debug_print(self, indent=''):
        print indent + 'flags', hex(self.flags)
        print indent + 'argc', self.argc
        print indent + 'localc', self.localc
        for i, block in enumerate(self.blocks):
            print indent + 'block', i
            pc = 0
            while pc < len(block):
                pc, opcode, args = dec_code(block, pc)
                print indent + " ", opname(opcode), args
        for i, func in enumerate(self.functions):
            print indent + 'function', i
            func.debug_print(indent + '  ')

def main():
    stream = bincode.decoder.open_file(String(u'kernel.lic'))
    assert stream.read(8) == bincode.common.header
    strtab = []
    function = read_function(stream, strtab)
    count = stream.read_integer()
    for i in range(count):
        strtab.append(stream.read_string())

    function.debug_print()

def read_function(stream, strtab):
    flags = stream.read_integer()
    argc = stream.read_integer()
    localc = stream.read_integer()
    blockc = stream.read_integer()
    blocks = []
    for i in range(blockc):
        length = stream.read_integer()
        blocks.append(stream.read(length))
    functions = []
    functionc = stream.read_integer()
    for i in range(functionc):
        functions.append(read_function(stream, strtab))
    return Function(strtab, flags, argc, localc, blocks, functions)

if __name__=='__main__': main()
