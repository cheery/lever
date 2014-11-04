from reader import read_file
from ffi import Signed, Unsigned, Struct, Union, Pointer, CFunc, Array
from object import Object, List, String, Symbol, Integer, null

class Interface(Object):
    def __init__(self, name, tp):
        self.name = name
        self.tp = tp

    def repr(self):
        return "<interface " + self.name + ">"

def sym_eq(node, name):
    return isinstance(node, Symbol) and node.string == name

class APISpec(Object):
    def __init__(self, source, names):
        self.unresolved = {}
        self.names = names.copy()

        for node in source:
            if not isinstance(node, List):
                raise Exception("api file must consists of lists: " + node.repr())
            if len(node) < 3 or not sym_eq(node[1], '=') or not isinstance(node[0], Symbol):
                raise Exception("api file lists must be of form (<name> = <body>): " + node.repr())
            name = node[0].string
            head = node[2]
            if isinstance(head, Integer) and len(node) == 3:
                self.names[name] = head
            elif sym_eq(head, 'opaque'):
                self.names[name] = Struct(None)
            elif sym_eq(head, 'struct'):
                self.names[name] = Struct(None)
                self.unresolved[name] = node
            else:
                self.unresolved[name] = node

    def resolve(self, name):
        if name not in self.unresolved:
            if name in self.names:
                return self.names[name]
            else:
                raise Exception("cannot resolve typespec of name: " + name)
        node = self.unresolved[name]
        head = node[2]
        if sym_eq(head, 'struct'):
            struct = self.names[name]
            struct.define(self.resolve_fields(node[3:len(node)]))
            self.unresolved.pop(name)
            return struct
        elif sym_eq(head, 'union'):
            struct = self.names[name] = Union(self.resolve_fields(node[3:len(node)]))
            self.unresolved.pop(name)
            return struct
        elif sym_eq(head, 'cfunc'):
            assert len(node) >= 4
            restype = node[3]
            argtypes = node[4:len(node)]
            self.names[name] = cfunc = self.resolve_cfunc(restype, argtypes)
            self.unresolved.pop(name)
            return cfunc
        else:
            assert len(node) >= 4, name + " " + str(len(node))
            restype = node[2]
            sym = node[3]
            argtypes = node[4:len(node)]
            assert isinstance(sym, Symbol)
            self.names[name] = interface = Interface(sym.string, self.resolve_cfunc(restype, argtypes))
            self.unresolved.pop(name)
            return interface

    def resolve_cfunc(self, restype_i, argtypes_i):
        if sym_eq(restype_i, 'void'):
            restype = null
        else:
            restype = self.resolve_type(restype_i)
        argtypes = []
        for argtype_i in argtypes_i:
            argtypes.append(self.resolve_type(argtype_i))
        return CFunc(restype, argtypes)

    def resolve_fields(self, fields):
        for node in fields:
            if not isinstance(node, List):
                raise Exception("api struct/union must consists of field lists: " + node.repr())
            if len(node) < 3 or not sym_eq(node[1], '=') or not isinstance(node[0], Symbol):
                raise Exception("api struct/union lists must be of form (<name> = <body>): " + node.repr())
            name = String(node[0].string)
            head = node[2]
            if sym_eq(head, 'array') and len(node) == 4:
                tp = self.resolve_type(node[3])
                return Array(tp)
            if sym_eq(head, 'array') and len(node) == 5:
                tp = self.resolve_type(node[3])
                assert isinstance(node[4], Value)
                return Array(tp, node[4].value)
            if len(node) != 3 and not isinstance(head, Symbol):
                raise Exception("only references allowed for now: " + node.repr())
            return List([name, self.resolve_type(head)])

    def resolve_type(self, node):
        if not isinstance(node, Symbol):
            raise Exception("expected a type: " + node.repr())
        string = node.string
        if string.endswith('*') and len(string) >= 1:
            if string == 'void*':
                return Pointer(null)
            return Pointer(self.resolve_type(Symbol(string[0:len(string)-1])))
        tp = self.resolve(string)
        if isinstance(tp, Interface):
            raise Exception("expected a type: " + node.repr())
        return tp
