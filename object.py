class Object:
    def invoke(self, argv):
        raise Exception("cannot invoke " + self.repr())

    def __getitem__(self, index):
        raise Exception("cannot iterate " + self.repr())

    def __len__(self):
        raise Exception("cannot iterate " + self.repr())

class List(Object):
    def __init__(self, items):
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)

    def repr(self):
        out = []
        for item in self.items:
            out.append(item.repr())
        return '(' + ' '.join(out) + ')'

class String(Object):
    def __init__(self, string):
        self.string = string

    def repr(self):
        return '"' + str(self.string) + '"'

class Symbol(Object):
    def __init__(self, string):
        self.string = string

    def repr(self):
        return str(self.string)

class Integer(Object):
    def __init__(self, value):
        self.value = value

    def repr(self):
        return str(self.value)

class Constant(Object):
    def __init__(self, name):
        self.name = name

    def repr(self):
        return self.name

class BuiltinFunction(Object):
    def __init__(self, func, name=None):
        self.func = func
        self.name = name if name is None else func.__name__

    def invoke(self, argv):
        return self.func(argv)

    def repr(self):
        return "<built in function " + self.name + ">"

true = Constant('true')
false = Constant('false')
null = Constant('null')
