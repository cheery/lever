import re
from rpython.rlib.objectmodel import compute_hash

class Error(Exception):
    def __init__(self, message):
        self.message = message

class Object:
    # The metaclass here takes care every object will get an interface.
    # So programmer doesn't need to do that.
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if name not in ('Object', 'Interface') and 'interface' not in dict:
                cls.interface = Interface(
                    parent = cls.__bases__[0].interface,
                    name = re.sub("(.)([A-Z]+)", r"\1_\2", name).lower())

    def call(self, argv):
        raise Error("cannot call " + self.repr())

    def getitem(self, index):
        raise Error("cannot getitem " + self.repr())

    def setitem(self, index, value):
        raise Error("cannot setitem " + self.repr())

    def getattr(self, index):
        try:
            return BoundMethod(self, index, self.interface.methods[index])
        except KeyError as e:
            raise Error(index + " not in " + self.repr())

    def setattr(self, index, value):
        raise Error("cannot set " + index + " in " + self.repr())

    def callattr(self, name, argv):
        return self.getattr(name).call(argv)

    def repr(self):
        return "<" + self.interface.name + ">"

    def hash(self):
        return compute_hash(self)

    def eq(self, other):
        return self is other

    @classmethod
    def instantiator(cls, fn):
        cls.interface.instantiate = fn
        return fn

class Interface(Object):
    # Should add possibility to freeze the interface?
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
        self.instantiate = None
        self.methods = {}

    def call(self, argv):
        if self.instantiate is None:
            raise Error("Cannot instantiate " + self.name)
        return self.instantiate(argv)

    def repr(self):
        return self.name

Interface.interface = Interface(None, "interface")
Interface.interface.parent = Interface.interface

null = Interface(None, "null")
null.interface = null
null.parent = null

Object.interface = Interface(null, "object")

class BoundMethod(Object):
    def __init__(self, obj, name, method):
        self.obj = obj
        self.name = name
        self.method = method

    def call(self, argv):
        argv.insert(0, self.obj)
        return self.method.call(argv)

    def repr(self):
        return self.obj.repr() + "." + self.name
