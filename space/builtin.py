from rpython.rlib import unroll
from interface import Object, null
import space

class Builtin(Object):
    _immutable_fields_ = ['func']
    def __init__(self, func, name=None):
        self.func = func
        self.name = name if name is not None else func.__name__.decode('utf-8')

    def call(self, argv):
        return self.func(argv)
    
    def repr(self):
        return u"<builtin %s>" % self.name

# Turns out signature would have been much better
# if it had allowed optional and variadic arguments too.
# So I changed it to allow that.
def signature(*argtypes, **keywords):
    topc = argc = len(argtypes)
    argc -= keywords.get("optional", 0)
    variadic = keywords.get("variadic", False)
    argi = unroll.unrolling_iterable(range(argc))
    argj = unroll.unrolling_iterable(range(argc, topc))
    def signature_decorator(func):
        def fancy_frame(argv):
            args = ()
            L = len(argv)
            if L < argc:
                raise space.OldError(u"expected at least %d arguments, received %d" % (argc, L))
            if L > topc and not variadic:
                raise space.OldError(u"expected maximum %d arguments, received %d" % (topc, L))
            for i in argi:
                arg = argv[i]
                if isinstance(arg, argtypes[i]):
                    args += (arg,)
                else:
                    raise expectations_error(i, argtypes[i].interface.name)
            for j in argj:
                if j < L:
                    arg = argv[j]
                    if arg is null:
                        arg = None
                    elif not isinstance(arg, argtypes[j]):
                        raise expectations_error(j, argtypes[j].interface.name)
                else:
                    arg = None
                args += (arg,)
            if variadic:
                args += (argv[min(topc, L):],)
            return func(*args)
        fancy_frame.__name__ = func.__name__
        return fancy_frame
    return signature_decorator

# Sometimes we may expect different things, so there needs to be a way to escape
# the signature when it is appropriate and drop back into expectations error
# if expectations are violated.
def expectations_error(index, name):
    return space.OldError(u"expected arg:%d is %s" % (index, name))
