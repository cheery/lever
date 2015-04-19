import re
from rpython.rlib.objectmodel import compute_hash

class Error(Exception):
    def __init__(self, message):
        self.message = message
        self.stacktrace = []

class Object:
    _immutable_fields_ = ['interface', 'flag', 'number', 'value', 'contents', 'data', 'string[*]', 'iterator', 'arity', 'methods', 'default']
    __slots__ = []
    __attrs__ = []
    # The metaclass here takes care every object will get an interface.
    # So programmer doesn't need to do that.
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if name not in ('Object', 'Interface') and 'interface' not in dict:
                cls.interface = Interface(
                    parent = cls.__bases__[0].interface,
                    name = re.sub("(.)([A-Z]+)", r"\1_\2", name).lower().decode('utf-8'))

    def call(self, argv):
        raise Error(u"cannot call " + self.repr())

    def getitem(self, index):
        raise Error(u"cannot getitem " + self.repr())

    def setitem(self, index, value):
        raise Error(u"cannot setitem " + self.repr())

    def iter(self):
        raise Error(u"cannot iterate " + self.repr())

    def getattr(self, index):
        try:
            return BoundMethod(self, index, self.__class__.interface.methods[index])
        except KeyError as e:
            raise Error(u"%s not in %s" % (index, self.repr()))

    def setattr(self, index, value):
        raise Error(u"cannot set %s in %s" % (index, self.repr()))

    def callattr(self, name, argv):
        return self.getattr(name).call(argv)

    def repr(self):
        return u"<%s>" % self.__class__.interface.name

    def hash(self):
        return compute_hash(self)

    def eq(self, other):
        return self is other

    @classmethod
    def instantiator(cls, fn):
        cls.interface.instantiate = fn
        return fn

    @classmethod
    def builtin_method(cls, fn):
        from builtin import Builtin
        builtin = Builtin(fn)
        cls.interface.methods[builtin.name] = builtin

class Interface(Object):
    _immutable_fields_ = ['instantiate?', 'methods']
    # Should add possibility to freeze the interface?
    def __init__(self, parent, name):
        assert isinstance(name, unicode)
        self.parent = parent
        self.name = name
        self.instantiate = None
        self.methods = {}

    def call(self, argv):
        if self.instantiate is None:
            raise Error(u"Cannot instantiate " + self.name)
        return self.instantiate(argv)

    def repr(self):
        return self.name

Interface.interface = Interface(None, u"interface")
Interface.interface.parent = Interface.interface

null = Interface(None, u"null")
null.interface = null
null.parent = null

Object.interface = Interface(null, u"object")

class BoundMethod(Object):
    def __init__(self, obj, name, method):
        self.obj = obj
        self.name = name
        self.method = method

    def call(self, argv):
        argv.insert(0, self.obj)
        return self.method.call(argv)

    def repr(self):
        return u"%s.%s" % (self.obj.repr(), self.name)
