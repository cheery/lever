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
        s = cast(arg, String).string_val
        b = s.encode('utf-8')
        os.write(0, sp + b)
        sp = " "
    os.write(0, "\n")

base_stem = {
    u"print": w_print,
}
