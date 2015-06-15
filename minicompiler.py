import bincode.common
import bincode.encoder
from collections import OrderedDict
from instruction_format import enc_code

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

def main():
    stringtab = StringTable()
    function = Function(0x0, 4, 10, [
        enc_code('jump', 1, 2, 3, 4),
        ''.join((
            enc_code('add', 1, 2, 3),
            enc_code('cond', 3, 4, 5),
        )),
    ], [
        Function(0x0, 1, 2, [], []),
    ])
    write_file('kernel.lic', function, stringtab)

class StringTable(object):
    def __init__(self):
        self.strings = OrderedDict()

    def get(self, string):
        string_table = self.strings
        if string in string_table:
            return string_table[string]
        string_table[string] = len(string_table)
        return string_table[string]

def write_file(pathname, entry, strtab):
    stream = bincode.encoder.open_file(pathname)
    stream.write(bincode.common.header)
    entry.dump(stream)
    # write string table
    stream.write_integer(len(strtab.strings))
    for string in strtab.strings:
        stream.write_string(string)

    stream.close()

if __name__=='__main__': main()
