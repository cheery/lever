from interface import Object, null
from rpython.rlib import jit
import space

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

class ShadowCell(Cell):
    _attrs_ = ['slot', 'link']
    def __init__(self, slot, link):
        self.slot = slot
        self.link = link

class Module(Object):
    _immutable_fields_ = ['extends', 'cells']
    def __init__(self, name, namespace, extends=None, frozen=False):
        self.extends = extends
        self.frozen = frozen
        self.name = name
        self.cells = {}
        for name in namespace:
            self.setattr_force(name, namespace[name])

    @jit.elidable
    def lookup(self, name):
        if self.extends is None:
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

    def getattr(self, name):
        try:
            cell = jit.promote(self.lookup(name))
            while isinstance(cell, ShadowCell):
                if cell.link is None:
                    return cell.slot
                cell = cell.link
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
            raise space.unwind(space.LFrozenError(self))
        return self.setattr_force(name, value)

    def setattr_force(self, name, value):
        try:
            cell = jit.promote(self.lookup(name))
            if isinstance(cell, FrozenCell):
                raise space.unwind(space.LFrozenError(self))
            elif isinstance(cell, MutableCell):
                cell.slot = value
            elif isinstance(cell, ShadowCell):
                cell.slot = value
                cell.link = None
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
