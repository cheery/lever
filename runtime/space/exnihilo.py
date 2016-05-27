import space
from interface import Object

class Exnihilo(Object):
    _immutable_fields_ = ['cells']
    __slots__ = ['cells']

    def __init__(self, cells):
        self.cells = cells

    def getattr(self, name):
        try:
            return self.cells[name]
        except KeyError:
            raise space.OldError(u"object contains no field %s" % name)

    def setattr(self, name, value):
        self.cells[name] = value
        return value

    def repr(self):
        cellnames = u""
        for cellname in self.cells.keys():
            if len(cellnames) > 0:
                cellnames += u", "
            cellnames += cellname

        return u"<exnihilo %s>" % cellnames

@Exnihilo.instantiator
def instantiate(argv):
    assert len(argv) == 0
    return Exnihilo({})
