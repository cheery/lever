from interface import Error, Object
from rpython.rlib.jit import elidable

class Cell:
    def __init__(self, slot):
        self.slot = slot

class Module(Object):
    _immutable_fields_ = ['extends', 'cells']
    def __init__(self, name, namespace, extends=None, frozen=False):
        self.extends = extends
        self.frozen = frozen
        self.name = name
        self.cells = {}
        for name in namespace:
            self.cells[name] = Cell(namespace[name])

    # This is likely not correct. It's likely the extends -slot values should be slowly copied over.
    # Alternatively the whole extends -concept could be dumb, and I should dump it.
    @elidable
    def lookup(self, name):
        if self.extends is None:
            return self.cells[name]
        try:
            return self.cells[name]
        except KeyError:
            return self.extends.lookup(name)

    def getattr(self, name):
        try:
            return self.lookup(name).slot
        except KeyError:
            return Object.getattr(self, name)

    def setattr(self, name, value):
        if self.frozen:
            raise Error(u"module %s is frozen" % self.name)
        return self.setattr_force(name, value)

    def setattr_force(self, name, value):
        if name not in self.cells:
            self.cells[name] = Cell(value)
        else:
            self.cells[name].slot = value
        return value

    def repr(self):
        return u"<module %s>" % self.name
