import os
from objects.common import *

# The first thing that needs to work properly
# are the function calls. This small test
# ensures that they do work.
def new_entry_point(config):
    def entry_point(raw_argv):
        s = String(u"hello")
        w = String(u"runtime")
        call(w_print, [s, w])
        return 0
    return entry_point

@builtin(vari=True)
def w_print(args):
    sp = ""
    for arg in args:
        s = cast(arg, String).string_val
        b = s.encode('utf-8')
        os.write(0, sp + b)
        sp = " "
    os.write(0, "\n")
