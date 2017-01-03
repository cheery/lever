from builtin import signature
import exnihilo
import operators
import space
from interface import Object, BoundMethod, null
from errors import OldError
from rpython.rlib import jit

class CustomObject(Object):
    _immutable_fields_ = ['custom_interface', 'map', 'storage']
    __slots__ = ['custom_interface', 'map', 'storage']
    def __init__(self, custom_interface):
        self.custom_interface = custom_interface
        self.map = exnihilo.EMPTY_MAP
        self.storage = []

    def call(self, argv):
        method = self.custom_interface.lookup_method(u"+call")
        if method is None:
            return Object.call(self, argv)
        else:
            return method.call([self] + argv)

    def getitem(self, index):
        method = self.custom_interface.lookup_method(u"+getitem")
        if method is None:
            return Object.getitem(self, index)
        else:
            return method.call([self, index])

    def setitem(self, index, value):
        method = self.custom_interface.lookup_method(u"+setitem")
        if method is None:
            return Object.setitem(self, index, value)
        else:
            return method.call([self, index, value])

    def iter(self):
        method = self.custom_interface.lookup_method(u"+iter")
        if method is None:
            return Object.iter(self)
        else:
            return method.call([self])

    def getattr(self, name):
        map = jit.promote(self.map)
        index = map.getindex(name)
        if index != -1:
            return self.storage[index]
        else:
            method = self.custom_interface.lookup_method(name)
            if method is None:
                return Object.getattr(self, name)
            elif isinstance(method, Property):
                return method.getter.call([self])
            else:
                return BoundMethod(self, name, method)

    def setattr(self, name, value): # TODO: figure out something that makes sense here.
        method = self.custom_interface.lookup_method(name)
        if isinstance(method, Property):
            return method.setter.call([self, value])
        map = jit.promote(self.map)
        index = map.getindex(name)
        if index != -1:
            self.storage[index] = value
        else:
            self.map = map.new_map_with_additional_attribute(name)
            self.storage.append(value)
        return value

    def contains(self, obj):
        method = self.custom_interface.lookup_method(u"+contains")
        if method is None:
            return Object.contains(self, obj)
        else:
            return space.is_true(method.call([self, obj]))

    def repr(self):
        method = self.custom_interface.lookup_method(u"+repr")
        if method is None:
            return Object.repr(self)
        else:
            result = method.call([self])
            assert isinstance(result, space.String)
            return result.string

    # TODO: figure out whether this matters to performance.
    def hash(self):
        method = self.custom_interface.lookup_method(u"+hash")
        if method is None:
            return Object.hash(self)
        else:
            result = method.call([self])
            assert isinstance(result, space.Integer)
            return int(result.value)

    def eq(self, other): # TODO: improve this.
        return space.is_true(operators.eq.call([self, other]))

def instantiate(interface, argv):
    obj = CustomObject(interface)
    method = interface.lookup_method(u"+init")
    if method is not None:
        method.call([obj] + argv)
    return obj
CustomObject.interface.instantiate = instantiate

class Property(Object):
    __slots__ = ['getter', 'setter']
    def __init__(self):
        self.getter = null
        self.setter = null

    def getattr(self, name):
        if name == u"get":
            return self.getter
        if name == u"set":
            return self.setter
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"get":
            self.getter = value
            return value
        if name == u"set":
            self.setter = value
            return value
        return Object.setattr(self, name, value)

@Property.instantiator2(signature())
def Property_instantiate():
    return Property()
