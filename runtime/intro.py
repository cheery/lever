from json_loader import read_json_file
from objects import *
import interpreter
import os

def new_entry_point(config):
    base_module = Module()
    for name in base_stem:
        base_module.assign(name, base_stem[name])

    def entry_point(raw_argv):
        try:
            obj = read_json_file(String(u"prelude/intro.lc.json"))
            env = [base_module]
            script = interpreter.read_script(obj, {}, env)
            call(script, [])
        except Traceback as tb:
            os.write(0, "Traceback (most recent call last):\n")
            for loc, sources in reversed(tb.trace):
                col0 = cast(loc[0], Integer).toint()
                lno0 = cast(loc[1], Integer).toint()
                col1 = cast(loc[2], Integer).toint()
                lno1 = cast(loc[3], Integer).toint()
                srci = cast(loc[4], Integer).toint()
                src = sources[srci].string_val.encode('utf-8')
                s = "  %d %d %d %d %s\n" % (col0, lno0, col1, lno1, src)
                os.write(0, s)
            os.write(0, tb.error.__class__.__name__ + "\n")
        return 0
    return entry_point

# The stem for the base module is defined outside the entry
# point generator. For now it is populated with 'print'.
# It provides some basic output that helps with testing that
# the program works.
@builtin(vari=True)
def w_print(args):
    sp = ""
    for arg in args:
        s = cast(call(op_stringify, [arg]), String).string_val
        b = s.encode('utf-8')
        os.write(0, sp + b)
        sp = " "
    os.write(0, "\n")

@builtin()
def w_ne(a,b):
    return boolean(call(op_eq, [a,b]) is true)

@builtin()
def w_ge(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i >= 0)

@builtin()
def w_gt(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i == 1)

@builtin()
def w_le(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i <= 0)

@builtin()
def w_lt(a,b):
    i = cast(call(op_cmp, [a,b]), Integer).toint()
    return boolean(i == -1)

base_stem = {
    u"print": w_print,
    u"==": op_eq,
    u"!=": w_ne,
    u"hash": op_hash,
    u"call": op_call,
    u"in": op_in,
    u"getitem": op_getitem,
    u"setitem": op_setitem,
    u"iter": op_iter,
    u"cmp": op_cmp,
    u">=": w_ge,
    u">": w_gt,
    u"<=": w_le,
    u"<": w_lt,
    u"++": op_concat,
    u"+": op_add,
    u"-": op_sub,
    u"*": op_mul,
    u"&": op_and,
    u"|": op_or,
    u"xor": op_xor,
    u"stringify": op_stringify,
    u"parse_integer": builtin()(parse_integer),
}
