from space import *
import ffi
import json, os

class Api(Object):
    def __init__(self, constants, functions, types):
        self.cache = {}
        self.typecache = {}
        self.constants = constants
        self.functions = functions
        self.types = types

    def getitem(self, name):
        if not isinstance(name, String):
            raise Error("API.getitem requires a string")
        name = name
        if name.string in self.cache:
            return self.cache[name.string]
        self.cache[name.string] = result = self.lookup(name)
        return result

    def lookup(self, name):
        if self.constants.contains(name):
            return self.constants.getitem(name)
        if self.functions.contains(name):
            decl = self.functions.getitem(name)
            return self.wrap_cfunc(decl)
        return self.lookup_type(name)

    def lookup_type(self, name):
        if isinstance(name, String):
            if name.string in self.typecache:
                return self.typecache[name.string]
            if name.string.endswith('*'):
                return ffi.Pointer(self.lookup_type(String(name.string[:-1])))
            if self.types.contains(name):
                decl = self.types.getitem(name)
                ctype = self.build_ctype(name.string, decl)
                return ctype
            if name.string in ffi.systemv.types:
                return ffi.systemv.types[name.string]
            if name.string == 'void':
                return null
        raise Error(name.repr() + " not in API")

    def build_ctype(self, name, decl):
        which = decl.getitem(String("type"))
        if isinstance(which, String) and which.string == "union":
            fields = decl.getitem(String("fields"))
            return ffi.Union(self.parse_fields(name, fields))
        if isinstance(which, String) and which.string == "struct":
            fields = decl.getitem(String("fields"))
            return ffi.Struct(self.parse_fields(name, fields))
        if isinstance(which, String) and which.string == "opaque":
            return ffi.Struct(None)
        raise Error(name + ": no ctype builder for " + which.repr())

    def parse_fields(self, name, fields_list):
        if not isinstance(fields_list, List):
            raise Error(name + ": ctype fields, expected list")
        fields = []
        for field in fields_list.contents:
            field_name = field.getitem(Integer(0))
            if not isinstance(field_name, String):
                raise Error(name + ": first column should be the name")
            ctype = self.lookup_type(field.getitem(Integer(1)))
            fields.append((field_name.string, ctype))
        return fields

    def wrap_cfunc(self, decl):
        cname = decl.getitem(String('name'))
        restype = decl.getitem(String('restype'))
        argtypes_list = decl.getitem(String('argtypes'))
        if not isinstance(cname, String):
            raise Error("incorrect function record")
        if not isinstance(argtypes_list, List):
            raise Error("incorrect function record")
        restype = self.lookup_type(restype)
        argtypes = []
        for argtype in argtypes_list.contents:
            argtypes.append(self.lookup_type(argtype))
        ctype = ffi.CFunc(restype, argtypes)
        return ffi.Wrap(cname.string, ctype)

def wrap(obj):
    if isinstance(obj, dict):
        dict_ = Dict()
        for key, value in obj.items():
            dict_.setitem(wrap(key), wrap(value))
        return dict_
    elif isinstance(obj, list):
        return List(map(wrap, obj))
    elif isinstance(obj, str):
        return String(obj)
    elif isinstance(obj, unicode):
        return String(obj.encode('utf-8'))
    elif isinstance(obj, int):
        return Integer(obj)
    else:
        assert False, repr(obj)

preloaded = {}

directory = 'headers'
for header in os.listdir(directory):
    with open(os.path.join(directory, header)) as fd:
        preloaded[header] = wrap(json.load(fd))

module = Module('api', {
}, frozen=True)

def builtin(fn):
    module.namespace[fn.__name__] = Builtin(fn)
    return fn

@builtin
@signature(String)
def open(path):
    path = path.string
    if path.endswith(".so"):
        path = path.rsplit('.', 1)[0]
    json_path = path + ".json"
    so_path = path + ".so"
    return ffi.Library.interface.call([String(so_path), open_api(json_path)])

def open_api(json_path):
    if json_path not in preloaded:
        raise Error(json_path + ": not found in preloaded headers")
    apispec = preloaded[json_path]
    api = Api(
        apispec.getitem(String("constants")),
        apispec.getitem(String("functions")),
        apispec.getitem(String("types")))
    return api
