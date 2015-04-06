from interface import Error, Object

class Module(Object):
    def __init__(self, name, namespace, extends=None, frozen=False):
        self.extends = extends
        self.frozen = frozen
        self.name = name
        self.namespace = namespace

    def lookup(self, name):
        if self.extends is None:
            return self.namespace[name]
        try:
            return self.namespace[name]
        except KeyError:
            return self.extends.lookup(name)

    def getattr(self, name):
        try:
            return self.lookup(name)
        except KeyError:
            return Object.getattr(self, name)

    def setattr(self, name, value):
        if self.frozen:
            raise Error("module " + self.name + " is frozen")
        self.namespace[name] = value
        return value

    def repr(self):
        return "<module " + self.name + ">"
