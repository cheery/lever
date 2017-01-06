import re
from rpython.rlib.objectmodel import compute_hash, specialize, always_inline
from rpython.rlib import jit
import space

class Object:
    _immutable_fields_ = ['interface', 'custom_interface', 'flag', 'number', 'value', 'contents', 'data', 'string[*]', 'iterator', 'arity', 'methods', 'default', 'cells']
    __slots__ = []
    __attrs__ = []
    # The metaclass here takes care every object will get an interface.
    # So programmer doesn't need to do that.
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if name not in ('Object', 'Interface', 'null') and 'interface' not in dict:
                cls.interface = Interface(
                    parent = cls.__bases__[0].interface,
                    name = re.sub("(.)([A-Z]+)", r"\1_\2", name).lower().decode('utf-8'))
                if re.match("^L[A-Z]", name):
                    cls.interface.name = name[1:].decode('utf-8')
                if name not in ('BoundMethod', 'Builtin', 'SourceLocationLines'):
                    expose_internal_methods(cls.interface, dict)

    def call(self, argv):
        raise space.unwind(space.LTypeError(u"cannot call " + self.repr()))

    def getitem(self, index):
        raise space.unwind(space.LKeyError(self, index))

    def setitem(self, index, value):
        raise space.unwind(space.LKeyError(self, index))

    def iter(self):
        raise space.unwind(space.LTypeError(u"cannot iterate " + self.repr()))

    def listattr(self):
        listing = []
        for name in self.__class__.interface.methods.keys():
            listing.append(space.String(name))
        return listing

    def getattr(self, index):
        method = self.__class__.interface.lookup_method(index)
        if method is not None:
            return BoundMethod(self, index, method)
        else:
            raise space.unwind(space.LAttributeError(self, index))

    def setattr(self, index, value):
        raise space.unwind(space.LAttributeError(self, index))

    def callattr(self, name, argv):
        return self.getattr(name).call(argv)

    def contains(self, obj):
        raise space.unwind(space.LTypeError(u"%s cannot contain" % self.repr()))

    def repr(self):
        return u"<%s>" % space.get_interface(self).name

    def hash(self):
        return compute_hash(self)

    def eq(self, other):
        return self is other

    @classmethod
    def instantiator(cls, fn):
        def _instantiate_b_(interface, argv):
            return fn(argv)
        cls.interface.instantiate = _instantiate_b_
        register_instantiator(cls.interface, fn)
        return fn

    @classmethod
    def instantiator2(cls, decorator):
        def _decorator_(fn):
            fn = decorator(fn)
            def _instantiate_wrapper_(interface, argv):
                return fn(argv)
            cls.interface.instantiate = _instantiate_wrapper_
            register_instantiator(cls.interface, fn)
            return fn
        return _decorator_

    @classmethod
    def builtin_method(cls, fn):
        from builtin import Builtin
        builtin = Builtin(fn)
        cls.interface.methods[builtin.name] = builtin

    @classmethod
    def method(cls, name, decorator):
        def _decarotar_(fn):
            from builtin import Builtin
            builtin = Builtin(decorator(fn), name)
            cls.interface.methods[builtin.name] = builtin
            return fn
        return _decarotar_

class Interface(Object):
    _immutable_fields_ = ['instantiate?', 'methods']
    # Should add possibility to freeze the interface?
    def __init__(self, parent, name):
        assert isinstance(name, unicode)
        self.parent = parent # TODO: make this matter for custom objects.
        self.name = name
        self.instantiate = None
        self.methods = {}
        if parent is not None:
            self.methods.update(parent.methods)
        self.doc = None

    def call(self, argv):
        if self.instantiate is None:
            if self.name == u'null':
                raise space.unwind(space.LTypeError(u"cannot call null"))
            raise space.unwind(space.LTypeError(u"cannot instantiate " + self.name))
        return self.instantiate(self, argv)

    def repr(self):
        return self.name

    def getattr(self, name):
        if name == u"doc":
            return null if self.doc is None else self.doc
        method = self.lookup_method(name)
        if method is not None:
            return method
        method = self.__class__.interface.lookup_method(name)
        if method is not None:
            return BoundMethod(self, name, method)
        return Object.getattr(self, name)

    @jit.elidable
    def lookup_method(self, name):
        return self.methods.get(name, None)

    def setattr(self, name, value):
        if name == u"doc":
            self.doc = value
            return null
        else:
            return Object.setattr(self, name, value)

    def listattr(self):
        listing = []
        listing.append(space.String(u"doc"))
        for methodname in self.methods.keys():
            listing.append(space.String(methodname))
        return listing

Interface.interface = Interface(None, u"interface")
Interface.interface.parent = Interface.interface

null = Interface(None, u"null")
null.interface = null
null.parent = null

Object.interface = Interface(null, u"object")

class BoundMethod(Object):
    _immutable_fields_ = ['obj', 'name', 'methodfn']
    def __init__(self, obj, name, methodfn):
        self.obj = obj
        self.name = name
        self.methodfn = methodfn

    def call(self, argv):
        return self.methodfn.call([self.obj] + argv)

    def getattr(self, name):
        return self.methodfn.getattr(name)

    def setattr(self, name, value):
        return self.methodfn.setattr(name, value)

    def listattr(self):
        return self.methodfn.listattr()

    def repr(self):
        return u"%s.%s" % (self.obj.repr(), self.name)

# Notice that cast != instantiation.
# The distinction is very important.
cast_methods = {}
def cast_for(cls):
    def _cast_decorator_(x):
        cast_methods[cls] = x
        return x
    return _cast_decorator_

# Cast didn't appear to handle well as a class method, so I made this
# convenient table construct that uses default handling when conversion
# is not available.

# User objects will not have access to implement this method of casting. 
# Userspace casting will be treated as separate problem.

# TODO: frame entry association could be "cool" here. So you would know
#       where a cast attempt failed.
@always_inline
@specialize.arg(1, 2)
def cast(x, cls, info=u"something"):
    if isinstance(x, cls): # This here means that cast won't change object
        return x           # if it is already correct type.
    try:
        fn = cast_methods[cls]
    except KeyError as _:
        raise space.unwind(space.LTypeError(u"expected %s is %s, got %s" % (
            info, cls.interface.name, x.repr())))
    res = fn(x)
    if isinstance(res, cls):
        return res
    # TODO: Consider alternative ways to say it. :)
    raise space.unwind(space.LTypeError(u"implicit conversion of %s at %s into %s returned %s" % (
        x.repr(), info, cls.interface.name, res.repr())))

# Variation of cast that accepts a null value and translates it to None.
@always_inline
@specialize.arg(1, 2)
def cast_n(x, cls, info=u"something"):
    if x is null:
        return None
    return cast(x, cls, info)


# Yes, this is a hacky hack.
import builtin
def expose_internal_methods(interface, methods):
    for name in methods:
        if name in internal_methods:
            interface.methods[u"+" + name.decode('utf-8')] = builtin.Builtin(
                hate_them,
                spec=internal_methods[name],
                source_location=builtin.get_source_location(methods[name]))

internal_methods = {
    u"call":     (0, 0, True,  ['argv'], None),
    u"getitem":  (0, 0, False, ['index'], None),
    u"setitem":  (0, 0, False, ['index', 'value'], None),
    u"iter":     (0, 0, False, [], None),
    #u"listattr": (0, 0, False, []),                      # TODO: figure out what to do with these.
    #u"getattr":  (0, 0, False, ['name'], None),          # these all are usually
    #u"setattr":  (0, 0, False, ['name', 'value'], None), # overloaded to handle attributes.
    u"contains": (0, 0, False, ['value'], None),
    u"repr":     (0, 0, False, [], None),
    u"hash":     (0, 0, False, [], None),
}

def register_instantiator(interface, fn):
    interface.methods[u"+init"] = builtin.Builtin(hate_them,
        spec=builtin.get_spec(fn),
        source_location=builtin.get_source_location(fn))

# Internal methods help at documenting the system.
def hate_them(argv):
    raise space.unwind(space.LError(u"no"))

#expose_internal_methods(Interface)
#expose_internal_methods(Object) # if I do this,
                                 # every method will have internal_methods
                                 # Besides, Object methods are placeholders.

# I doubt we miss these.
#expose_internal_methods(BoundMethod)
#expose_internal_methods(builtin.Builtin)
#expose_internal_methods(builtin.SourceLocationLines)

# When your good names are your best.
@Interface.instantiator2(builtin.signature(Object))
def Interface_init_is_cast(obj):
    return space.get_interface(obj)
