import space
from interface import Object, BoundMethod, Error

class CustomObject(Object):
    _immutable_fields_ = ['custom_interface', 'cells']
    __slots__ = ['custom_interface', 'cells']
    def __init__(self, custom_interface, cells):
        self.custom_interface = custom_interface
        self.cells = cells

    def call(self, argv):
        try:
            method = self.custom_interface.methods[u"+call"]
        except KeyError as error:
            return Object.call(self, argv)
        else:
            return method.call([self] + argv)

    def getitem(self, index):
        try:
            method = self.custom_interface.methods[u"+getitem"]
        except KeyError as error:
            return Object.getitem(self, index)
        else:
            return method.call([self, index])

    def setitem(self, index, value):
        try:
            method = self.custom_interface.methods[u"+setitem"]
        except KeyError as error:
            return Object.setitem(self, index, value)
        else:
            return method.call([self, index, value])

    def iter(self):
        try:
            method = self.custom_interface.methods[u"+iter"]
        except KeyError as error:
            return Object.iter(self)
        else:
            return method.call([self])

    def getattr(self, index):
        try:
            return self.cells[index]
        except KeyError as e:
            try:
                return BoundMethod(self, index, self.custom_interface.methods[index])
            except KeyError as e:
                raise Error(u"%s not in %s" % (index, self.repr()))

    def setattr(self, index, value): # TODO: figure out something that makes sense here.
        self.cells[index] = value

    def contains(self, obj):
        try:
            method = self.custom_interface.methods[u"+contains"]
        except KeyError as error:
            return Object.contains(self, obj)
        else:
            return space.is_true(method.call([self, obj]))

    def repr(self):
        try:
            method = self.custom_interface.methods[u"+repr"]
        except KeyError as error:
            return Object.repr(self)
        else:
            result = method.call([self])
            assert isinstance(result, space.String)
            return result.string

    # TODO: figure out whether this matters to performance.
    def hash(self):
        try:
            method = self.custom_interface.methods[u"+hash"]
        except KeyError as error:
            return Object.hash(self)
        else:
            result = method.call([self])
            assert isinstance(result, space.Integer)
            return int(result.value)

    def eq(self, other): # TODO: improve this.
        return Object.eq(self, other)

def instantiate(interface, argv):
    obj = CustomObject(interface, {})
    try:
        method = interface.methods[u"+init"]
    except KeyError as error:
        pass
    else:
        method.call([obj] + argv)
    return obj
CustomObject.interface.instantiate = instantiate
