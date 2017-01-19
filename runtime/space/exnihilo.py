import space
from builtin import signature
from interface import Object
from rpython.rlib import jit

class Exnihilo(Object):
    _immutable_fields_ = ['storage']
    __slots__ = ['map', 'storage']

    def __init__(self):
        self.map = EMPTY_MAP
        self.storage = []

    def getattr(self, name):
        map = jit.promote(self.map)
        index = map.getindex(name)
        if index != -1:
            return self.storage[index]
        else:
            return Object.getattr(self, name)

    def setattr(self, name, value):
        map = jit.promote(self.map)
        index = map.getindex(name)
        if index != -1:
            self.storage[index] = value
        else:
            self.map = map.new_map_with_additional_attribute(name)
            self.storage.append(value)
        return value

    def listattr(self):
        listing = Object.listattr(self)
        for name in self.map.attribute_indexes:
            listing.append(space.String(name))
        return listing

    def repr(self):
        cellnames = u""
        for cellname in self.map.attribute_indexes:
            if len(cellnames) > 0:
                cellnames += u", "
            cellnames += cellname

        return u"<object %s>" % cellnames

# Exnihilo doesn't exist for the user. He only sees an object.
Exnihilo.interface = Object.interface

@Object.instantiator2(signature(Object, optional=1))
def instantiate(obj):
    res = Exnihilo()
    if obj is not None:
        obj = space.cast(obj, space.Dict, u"object instantiation")
        for key, value in obj.data.items():
            key = space.cast(key, space.String, u"setattr")
            res.setattr(key.string, value)
    return res

# Attribute optimization for exnihilo objects.
class Map(object):
    def __init__(self):
        self.attribute_indexes = {}
        self.other_maps = {}

    @jit.elidable
    def getindex(self, name):
        return self.attribute_indexes.get(name, -1)

    @jit.elidable
    def new_map_with_additional_attribute(self, name):
        if name not in self.other_maps:
            newmap = Map()
            newmap.attribute_indexes.update(self.attribute_indexes)
            newmap.attribute_indexes[name] = len(self.attribute_indexes)
            self.other_maps[name] = newmap
        return self.other_maps[name]

EMPTY_MAP = Map()
