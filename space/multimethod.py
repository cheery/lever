from builtin import Builtin, signature
from interface import Error, Object
from listobject import List
from rpython.rlib.objectmodel import compute_hash, r_dict
from rpython.rlib import jit

def eq_fn(this, other):
    return this.eq(other)

def hash_fn(this):
    return this.hash()

class Multimethod(Object):
    _immutable_fields_ = ['arity', 'methods']
    def __init__(self, arity, default=None):
        self.arity = arity
        self.methods = r_dict(eq_fn, hash_fn, force_non_null=True)
        self.default = default

    def call(self, argv):
        return self.invoke_method(argv, suppress_default=False)

    def call_suppressed(self, argv):
        return self.invoke_method(argv, suppress_default=True)

    @jit.elidable
    def get_method(self, *interfaces):
        return self.methods.get(List(list(interfaces)), None)

    @jit.unroll_safe
    def invoke_method(self, argv, suppress_default):
        self = jit.promote(self)
        if len(argv) < self.arity:
            raise Error(u"expected at least %d arguments, got %d" % (self.arity, len(argv))) 
        if self.arity == 1:
            method = self.get_method(jit.promote(argv[0].interface))
        elif self.arity == 2:
            method = self.get_method(
                jit.promote(argv[0].interface),
                jit.promote(argv[1].interface))
        elif self.arity == 3:
            method = self.get_method(
                jit.promote(argv[0].interface),
                jit.promote(argv[1].interface),
                jit.promote(argv[2].interface))
        elif self.arity == 4:
            method = self.get_method(
                jit.promote(argv[0].interface),
                jit.promote(argv[1].interface),
                jit.promote(argv[2].interface),
                jit.promote(argv[3].interface))
        else:
            vec = []
            for i in range(self.arity):
                vec.append(argv[i].interface)
            method = self.methods.get(List(vec), None)
        if method is None:
            vec = []
            for i in range(self.arity):
                vec.append(argv[i].interface)
            if self.default is None or suppress_default:
                names = []
                for i in range(self.arity):
                    names.append(vec[i].name)
                raise Error(u"no method for ["+u' '.join(names)+u"]")
            return self.default.call(argv)
        return method.call(argv)

    def multimethod(self, *spec):
        vec = List(list(cls.interface for cls in spec))
        def _impl_(fn):
            self.methods[vec] = Builtin(fn)
            return fn
        return _impl_

    def multimethod_s(self, *spec):
        def _impl_(fn):
            return self.multimethod(*spec)(signature(*spec)(fn))
        return _impl_
