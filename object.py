import re
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.objectmodel import compute_hash, r_dict

class Error(Exception):
    def __init__(self, message):
        self.message = message

def system_hash(obj):
    return obj.system_hash()

def system_eq(obj, other):
    return obj.system_eq(other)

class Object:
    class __metaclass__(type):
        def __init__(cls, name, bases, dict):
            if name not in ('Object', 'Interface') and 'interface' not in dict:
                cls.interface = Interface(
                    name=re.sub("(.)([A-Z]+)", r"\1 \2", name).lower())

    def invoke(self, argv):
        raise Exception("cannot invoke " + self.repr())

    def getitem(self, index):
        raise Exception("cannot [] " + self.repr())

    def setitem(self, index, value):
        raise Exception("cannot []= " + self.repr())

    def getattr(self, name):
        raise Exception("cannot ." + name + " " + self.repr())

    def setattr(self, name, value):
        raise Exception("cannot ." + name + "= " + self.repr())

    def callattr(self, name, argv):
        return self.getattr(name).invoke(argv)
#
#    def __getitem__(self, index):
#        raise Exception("cannot iterate " + self.repr())
#
#    def __len__(self):
#        raise Exception("cannot iterate " + self.repr())

    def system_hash(self):
        return compute_hash(self)

    def system_eq(self, other):
        return self is other

    def repr(self):
        return "<" + self.interface.name + ">"

class Interface(Object):
    def __init__(self, name):
        self.name = name

Interface.interface = Interface("interface")

class List(Object):
    def __init__(self, items):
        self.items = items

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        return self.items[index]

    def __len__(self):
        return len(self.items)

    def system_hash(self):
        mult = 1000003
        x = 0x345678
        z = len(self.items)
        for w_item in self.items:
            y = w_item.system_hash()
            x = (x ^ y) * mult
            z -= 1
            mult += 82520 + z + z
        x += 97531
        return intmask(x)

    def system_eq(self, other):
        if not isinstance(other, List):
            return False
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if not self[i].system_eq(other[i]):
                return False
        return True

    def getattr(self, name):
        if name == 'length':
            return Integer(len(self.items))
        return Object.getattr(self, name)

    def getitem(self, index):
        assert isinstance(index, Integer)
        if not 0 <= index.value < len(self.items):
            raise Exception("index out of range")
        return self.items[index.value]

    def setitem(self, index, value):
        assert isinstance(index, Integer)
        if not 0 <= index.value < len(self.items):
            raise Exception("index out of range")
        self.items[index.value] = value
        return value

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

    def system_hash(self):
        return compute_hash(self.string)

    def system_eq(self, other):
        return self.string == other.string

class Symbol(Object):
    def __init__(self, string):
        self.string = string

    def repr(self):
        return str(self.string)

    def system_hash(self):
        return compute_hash(self.string)

    def system_eq(self, other):
        return self.string == other.string

class Integer(Object):
    def __init__(self, value):
        self.value = value

    def repr(self):
        return str(self.value)

    def system_hash(self):
        return compute_hash(self.value)

    def system_eq(self, other):
        return self.value == other.value

class Null(Object):
    def repr(self):
        return 'null'

class Boolean(Object):
    def __init__(self, flag):
        self.flag = flag

    def repr(self):
        if self.flag:
            return "true"
        else:
            return "false"

class BuiltinFunction(Object):
    def __init__(self, func, name=None):
        self.func = func
        self.name = name if name is not None else func.__name__

    def invoke(self, argv):
        return self.func(argv)

    def repr(self):
        return "<built in function " + self.name + ">"


class Module(Object):
    def __init__(self, name, namespace, frozen=False):
        self.name = name
        self.namespace = namespace
        self.frozen = frozen

    def getattr(self, name):
        return self.namespace[name]

    def setattr(self, name, value):
        if self.frozen:
            raise Exception("cannot ." + name + "= frozen module" + self.name)
        self.namespace[name] = value
        return value

    def repr(self):
        return "<module " + self.name + ">"

class Multimethod(Object):
    def __init__(self, arity, default=None):
        self.arity = arity
        self.methods = r_dict(system_eq, system_hash, force_non_null=True)
        self.default = default

    def invoke(self, argv):
        return self.invoke_method(argv, False)

    def invoke_method(self, argv, suppress_default):
        if len(argv) < self.arity:
            raise Error("expected "+str(self.arity)+" arguments, got "+str(len(argv)))
        typevec = []
        for i in range(self.arity):
            typevec.append(argv[i].interface)
        method = self.methods.get(List(typevec), None)
        if method is None:
            if self.default is None or suppress_default:
                names = []
                for i in range(self.arity):
                    names.append(argv[i].interface.name)
                raise Error("no method for ("+' '.join(names)+")")
            return self.default.invoke(argv)
        else:
            return method.invoke(argv)

    def register(self, *spec):
        typevec = List(list(cls.interface for cls in spec))
        def _impl_(fn):
            self.methods[typevec] = BuiltinFunction(fn)
            return fn
        return _impl_

true = Boolean(True)
false = Boolean(False)
null = Null()
