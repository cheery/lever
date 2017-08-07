from interface import Object, null
from builtin import signature
from rpython.rlib import jit
import space

class Cell:
    _attrs_ = []
    def getval(self):
        assert False, "abstract"

    def setval(self, value):
        assert False, "abstract"

class MutableCell(Cell):
    _attrs_ = ['slot']
    def __init__(self, slot):
        self.slot = slot

    def getval(self):
        return self.slot

    def setval(self, value):
        self.slot = value

class FrozenCell(Cell):
    _attrs_ = ['slot']
    _immutable_fields_ = ['slot']
    def __init__(self, slot):
        self.slot = slot

    def getval(self):
        return self.slot

    def setval(self, value):
        assert False, "frozen"

class ShadowCell(Cell):
    _attrs_ = ['slot', 'link']
    _immutable_fields_ = ['link?']  # Accessing a parent value and
    def __init__(self, slot, link): # then overwriting it is a rare operation.
        self.slot = slot
        self.link = link

    def getval(self):
        if self.link is None:
            return self.slot
        else:
            return self.link.getval()

    def setval(self, value):
        self.slot = value
        self.link = None

class Module(Object):
    _immutable_fields_ = ['extends', 'cells']
    def __init__(self, name, namespace, extends=None, frozen=False):
        self.extends = extends
        self.frozen = frozen
        self.name = name
        self.cells = {}
        self.setattr_force(u"doc", null)
        for name in namespace:
            self.setattr_force(name, namespace[name])

    @jit.elidable
    def lookup(self, name, to_set=False):
        if self.extends is None or to_set:
            return self.cells[name]
        try:
            return self.cells[name]
        except KeyError:
            link = self.extends.lookup(name)
            self.cells[name] = cell = ShadowCell(null, link)
            return cell

    def list_locals(self):
        out = []
        for name, cell in self.cells.items():
            if isinstance(cell, ShadowCell) and cell.link is not None:
                continue
            out.append(name)
        return out

    def listattr(self):
        listing = Object.listattr(self)
        for name, cell in self.cells.items():
            if isinstance(cell, ShadowCell) and cell.link is not None:
                continue
            listing.append(space.String(name))
        return listing

    @jit.look_inside
    def getattr(self, name):
        try:
            cell = jit.promote(self.lookup(name))
            return cell.getval()
        except KeyError:
            return Object.getattr(self, name)

    @jit.look_inside
    def setattr(self, name, value):
        if self.frozen:
            raise space.unwind(space.LFrozenError(self))
        try:
            cell = jit.promote(self.lookup(name, True))
            cell.setval(value)
        except KeyError:
            self.cells[name] = MutableCell(value)
        return value

    def setattr_force(self, name, value):
        try:
            cell = jit.promote(self.lookup(name, True))
            if isinstance(cell, FrozenCell):
                if name == u'doc' and cell.slot == null: # this is implicit set, so we allow it.
                    self.cells[name] = FrozenCell(value) # violates the elidable -rule.
                else:
                    raise space.unwind(space.LFrozenError(self))
            else:
                cell.setval(value)
        except KeyError:
            if self.frozen:
                self.cells[name] = FrozenCell(value)
            else:
                self.cells[name] = MutableCell(value)
        return value

    def repr(self):
        return u"<module %s>" % self.name
