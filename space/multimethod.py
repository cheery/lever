from interface import Error, Object
from rpython.rlib.objectmodel import compute_hash, r_dict
from builtin import Builtin

def eq_fn(this, other):
    return this.eq(other)

def hash_fn(this):
    return this.hash()

class Multimethod(Object):
    def __init__(self, arity, default=None):
        self.arity = arity
        self.methods = r_dict(eq_fn, hash_fn, force_non_null=True)
        self.default = default

    def call(self, argv):
        return self.invoke(self, argv, suppress_default)

    def invoke_method(self, argv, suppress_default):
        if len(argv) < self.arity:
            raise Error("expected at least " + str(self.arity) + " arguments, got " + str(len(argv)))
        vec = []
        for i in range(self.arity):
            vec.append(argv[i].interface)
        method = self.methods.get(List(vec), None)
        if method is None:
            if self.default is None or suppress_default:
                names = []
                for i in range(self.arity):
                    names.append(vec[i].name)
                raise Error("no method for ["+' '.join(name)+"]")
            return self.default.call(argv)
        return method.call(argv)

    def multimethod(self, *spec):
        vec = List(list(cls.interface for cls in spec))
        def _impl_(fn):
            self.methods[vec] = Builtin(fn)
            return fn
        return _impl_
