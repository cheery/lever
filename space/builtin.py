from rpython.rlib import unroll
from interface import Error, Object

class Builtin(Object):
    def __init__(self, func, name=None):
        self.func = func
        self.name = name if name is not None else func.__name__

    def call(self, argv):
        return self.func(argv)
    
    def repr(self):
        return "<builtin " + self.name + ">"

# Complete signature would include
# optional and variadic arguments too.
# Just this simple signature
# parser provides plenty of help.
def signature(*argt):
    argc = len(argt)
    argi = unroll.unrolling_iterable(range(argc))
    def _impl_(func):
        def fancy_frame(argv):
            args = ()
            if len(argv) < argc:
                raise Error("expected " + str(argc) + " arguments")
            for i in argi:
                arg = argv[i]
                if isinstance(arg, argt[i]):
                    args += (arg,)
                else:
                    raise Error("expected " + argt[i].interface.name + "as arg:" + str(i))
            return func(*args)
        fancy_frame.__name__ = func.__name__
        return fancy_frame
    return _impl_
