from rpython.rlib import unroll
from interface import Error, Object

class Builtin(Object):
    _immutable_fields_ = ['func']
    def __init__(self, func, name=None):
        self.func = func
        self.name = name if name is not None else func.__name__.decode('utf-8')

    def call(self, argv):
        return self.func(argv)
    
    def repr(self):
        return u"<builtin %s>" % self.name

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
                raise Error(u"expected %d arguments" % argc)
            for i in argi:
                arg = argv[i]
                if isinstance(arg, argt[i]):
                    args += (arg,)
                else:
                    raise Error(u"expected %s as arg: %d" % (argt[i].interface.name, i))
            return func(*args)
        fancy_frame.__name__ = func.__name__
        return fancy_frame
    return _impl_
