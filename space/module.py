from interface import Error, Object
from rpython.rlib import jit

class Cell:
    _attrs_ = []

class MutableCell(Cell):
    _attrs_ = ['slot']
    def __init__(self, slot):
        self.slot = slot

class FrozenCell(Cell):
    _attrs_ = ['slot']
    _immutable_fields_ = ['slot']
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
            self.setattr_force(name, namespace[name])

    # This is likely not correct. It's likely the extends -slot values should be slowly copied over.
    # Alternatively the whole extends -concept could be dumb, and I should dump it.
    @jit.elidable
    def lookup(self, name, assign=False):
        if assign or self.extends is None:
            return self.cells[name]
        try:
            return self.cells[name]
        except KeyError:
            return self.extends.lookup(name)

    def getattr(self, name):
        try:
            cell = jit.promote(self.lookup(name))
            if isinstance(cell, FrozenCell):
                return cell.slot
            elif isinstance(cell, MutableCell):
                return cell.slot
            else:
                assert False
        except KeyError:
            return Object.getattr(self, name)

    def setattr(self, name, value):
        if self.frozen:
            raise Error(u"module %s is frozen" % self.name)
        return self.setattr_force(name, value)

    def setattr_force(self, name, value):
        try:
            cell = jit.promote(self.lookup(name, assign=True))
            if isinstance(cell, FrozenCell):
                raise Error(u"cell %s is frozen" % name)
            elif isinstance(cell, MutableCell):
                cell.slot = value
            else:
                assert False
        except KeyError:
            if self.frozen:
                self.cells[name] = FrozenCell(value)
            else:
                self.cells[name] = MutableCell(value)
        return value

    def repr(self):
        return u"<module %s>" % self.name
