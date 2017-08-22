from builtin import Builtin, signature
from numbers import Integer
from interface import Object, null
from rpython.rlib import jit
from rpython.rlib.objectmodel import compute_hash, r_dict
from rpython.rlib.rarithmetic import intmask
from errors import OldError
import space, weakref

def eq_fn(this, other):
    if len(this) != len(other):
        return False
    for i in range(len(this)):
        if not this[i] is other[i]:
            return False
    return True

def hash_fn(this):
    mult = 1000003
    x = 0x345678
    z = len(this)
    for item in this:
        y = compute_hash(item)
        x = (x ^ y) * mult
        z -= 1
        mult += 82520 + z + z
    x += 97531
    return intmask(x)

class Multimethod(Object):
    _immutable_fields_ = ['arity', 'multimethod_table', 'default?', 'version?']
    def __init__(self, arity, default=null, doc=null):
        self.arity = arity
        self.multimethod_table = r_dict(eq_fn, hash_fn, force_non_null=True)
        self.version = VersionTag() # The version tag is required because the result 'None'
                                    # from the get_impl/get_method can be very useful due
                                    # to the .default -function call behavior.
        self.default = default
        self.doc = doc

    def call(self, argv):
        return self.invoke_method(argv, suppress_default=False)

    def call_suppressed(self, argv):
        return self.invoke_method(argv, suppress_default=True)

    def get_interface(self, obj, version):
        interface = space.get_interface(obj)
        return self.get_impl(interface, version)

    @jit.elidable
    def get_impl(self, interface, version):
        impl = interface
        while impl is not null:
            if self in impl.multimethod_index:
                return impl
            if impl.parent is impl: # interface loop
                return interface
            impl = impl.parent
        return interface

    @jit.elidable
    def get_method(self, version, *interface):
        interface = list(interface)
        face = [item.weakref for item in interface]
        return self.multimethod_table.get(face, None)

    @jit.unroll_safe
    def invoke_method(self, argv, suppress_default):
        self = jit.promote(self)
        if len(argv) < self.arity:
            raise OldError(u"expected at least %d arguments, got %d" % (self.arity, len(argv))) 
        method = self.fetch_method(argv, suppress_default)
        if method is None:
            vec = []
            for i in range(self.arity):
                vec.append(space.get_interface(argv[i]))
            names = []
            for i in range(self.arity):
                names.append(vec[i].name)
            raise OldError(u"no method for ["+u' '.join(names)+u"]")
        return method.call(argv)

    @jit.unroll_safe
    def fetch_method(self, argv, suppress_default):
        v = jit.promote(self.version)
        self = jit.promote(self)
        if self.arity == 1:
            method = self.get_method(v,
                jit.promote(self.get_interface(argv[0], v)))
        elif self.arity == 2:
            method = self.get_method(v,
                jit.promote(self.get_interface(argv[0], v)),
                jit.promote(self.get_interface(argv[1], v)))
        elif self.arity == 3:
            method = self.get_method(v,
                jit.promote(self.get_interface(argv[0], v)),
                jit.promote(self.get_interface(argv[1], v)),
                jit.promote(self.get_interface(argv[2], v)))
        elif self.arity == 4:
            method = self.get_method(v,
                jit.promote(self.get_interface(argv[0], v)),
                jit.promote(self.get_interface(argv[1], v)),
                jit.promote(self.get_interface(argv[2], v)),
                jit.promote(self.get_interface(argv[3], v)))
        else:
            vec = []
            for i in range(self.arity):
                vec.append(self.get_interface(argv[i], v).weakref)
            method = self.multimethod_table.get(vec, None)
        if method is not None:
            method = method()
            if method is not None:
                return method
        if self.default is null or suppress_default:
            return method
        else:
            return self.default

    def multimethod(self, *spec):
        vec = [cls.interface.weakref for cls in spec]
        def _impl_(fn):
            bfn = Builtin(fn)
            record = MultimethodRecord(self, vec, bfn)
            self.register_record(record)
            return fn
        return _impl_

    def multimethod_s(self, *spec):
        def _impl_(fn):
            self.multimethod(*spec)(signature(*spec)(fn))
            return fn
        return _impl_

    def getitem(self, index):
        index = space.cast(index, space.List, u"Multimethod.getitem")
        try:
            vec = [cls.interface.weakref for cls in index.contents]
            item = self.multimethod_table[vec]()
            if item is not None:
                return item
        except KeyError as _:
            pass
        raise space.unwind(space.LKeyError(self, index))

    def setitem(self, index, value):
        index = space.cast(index, space.List, u"Multimethod.setitem")
        vec = [
            space.cast(item,
                space.Interface,
                u"Multimethod expects interface list").weakref
            for item in index.contents]
        if vec in self.multimethod_table:
            raise space.unwind(space.LError(u"Multimethod table is not overwritable."))
        record = MultimethodRecord(self, vec, value)
        self.register_record(record)
        return value

    def getattr(self, index):
        if index == u"arity":
            return space.Integer(self.arity)
        if index == u"default":
            return self.default
        if index == u"doc":
            return self.doc
        if index == u"size":                # Used for ensuring that the gc+sleep can
            a = len(self.multimethod_table) # bite into the weak references.
            return Integer(a)
        return Object.getattr(self, index)

    def setattr(self, index, value):
        if index == u"default":
            self.default = value
            return value
        if index == u"doc":
            self.doc = value
            return value
        return Object.setattr(self, index, value)

    def register_record(self, record):
        self.multimethod_table[record.vec] = weakref.ref(record.function)
        for i in record.vec:
            interface = i.weakref()
            interface.multimethods[record] = None
            if self in interface.multimethod_index:
                interface.multimethod_index[self] += 1
            else:
                interface.multimethod_index[self] = 1
        self.version = VersionTag()

    def unregister_record(self, record):
        if record.vec not in self.multimethod_table:
            return # Can be called many times.
        self.multimethod_table.pop(record.vec)
        for i in record.vec:
            interface = i.weakref()
            if interface is None: # If the interface is None, it means that it's
                continue          # going to disappear soon and we don't care.
            # Interface may appear many times in a single record.
            interface.multimethods.pop(record, None)
            # But the multimethod_index is updated for each occurrence.
            interface.multimethod_index[self] -= 1
            if interface.multimethod_index[self] == 0:
                interface.multimethod_index.pop(self)
                self.version = VersionTag() # In the rare case that the interface
                                            # disappears and uncovers parent
                                            # interface's methods.

@Multimethod.instantiator
@signature(Integer)
def _(arity):
    return Multimethod(arity.value)

@Multimethod.method(u"call_suppressed", signature(Multimethod, variadic=True))
def Multimethod_call_suppressed(mm, args):
    return mm.call_suppressed(args)

@Multimethod.method(u"keys", signature(Multimethod))
def Multimethod_keys(self):
    out = []
    for vec in self.multimethod_table:
        argt = []
        for w in vec:
            item = w.weakref()
            if item is None:
                break
            argt.append(item)
        if len(argt) == len(vec):
            out.append(space.List(argt))
    return space.List(out)

class VersionTag(object):
    pass

# This is placed into the Interface.multimethods
class MultimethodRecord(object):
    _immutable_fields_ = ['multimethod', 'vec', 'function']
    def __init__(self, multimethod, vec, function):
        self.multimethod = multimethod
        self.vec = vec
        self.function = function
