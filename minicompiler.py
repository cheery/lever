from bincode.encoder import StringTable, Function, dump_function
from instruction_format import enc_code

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
    dump_function('kernel.lic', function, stringtab)

if __name__=='__main__': main()
