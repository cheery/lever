from interface import Object

class Builtin(Object):
    def __init__(self, func, name=None):
        self.func = func
        self.name = name if name is not None else func.__name__

    def call(self, argv):
        return self.func(argv)
    
    def repr(self):
        return "<builtin " + self.name + ">"
