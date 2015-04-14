from space import *
import ffi
import json, os

class ApiConfig:
    def __init__(self):
        self.headers_dir = 'headers'

conf = ApiConfig()

def init(argv):
    app_dir = os.environ.get('PYLLISP_PATH')
    if app_dir is None:
        app_dir = ''
    conf.headers_dir = os.path.join(app_dir, 'headers')

def dirname(p):
    """Returns the directory component of a pathname, adjusted for rpython"""
    i = p.rfind('/')
    if i > 0:
        return p[:i]
    elif i == 0:
        return p[:1]
    else:
        return ""

def get_header(path):
    return os.path.join(conf.headers_dir, path.encode('utf-8'))

class Api(Object):
    def __init__(self, constants, types, variables):
        self.cache = {}
        self.typecache = {}
        self.constants = constants
        self.types = types
        self.variables = variables

    def getitem(self, name):
        if not isinstance(name, String):
            raise Error(u"API.getitem requires a string")
        name = name
        if name.string in self.cache:
            return self.cache[name.string]
        self.cache[name.string] = result = self.lookup(name)
        return result

    def lookup(self, name):
        if self.constants.contains(name):
            return self.constants.getitem(name)
        if self.variables.contains(name):
            decl = self.variables.getitem(name)
            cname = decl.getitem(String(u"name"))
            if not isinstance(cname, String):
                raise Error(u"incorrect name record")
            if not isinstance(name, String):
                raise Error(u"incorrect name record")
            ctype = decl.getitem(String(u"type"))
            return ffi.Wrap(cname.string, self.build_ctype(name.string, ctype))
        return self.lookup_type(name)

    def lookup_type(self, name):
        if isinstance(name, String):
            if name.string in self.typecache:
                return self.typecache[name.string]
            if name.string.endswith(u'*'):
                ctype = ffi.Pointer(self.lookup_type(String(name.string[:-1])))
                self.typecache[name.string] = ctype
                return ctype
            if self.types.contains(name):
                decl = self.types.getitem(name)
                ctype = self.build_ctype(name.string, decl)
                self.typecache[name.string] = ctype
                return ctype
            if name.string in ffi.systemv.types:
                return ffi.systemv.types[name.string]
            if name.string == u'void':
                return null
            raise Error(name.repr() + u" not in API")
        else:
            return self.build_ctype(u"<unnamed>", name)

    def build_ctype(self, name, decl):
        which = decl.getitem(String(u"type"))
        if isinstance(which, String) and which.string == u"cfunc":
            restype = decl.getitem(String(u'restype'))
            argtypes_list = decl.getitem(String(u'argtypes'))
            if not isinstance(argtypes_list, List):
                raise Error(u"incorrect function record")
            restype = self.lookup_type(restype)
            argtypes = []
            for argtype in argtypes_list.contents:
                argtypes.append(self.lookup_type(argtype))
            return ffi.CFunc(restype, argtypes)
        if isinstance(which, String) and which.string == u"union":
            fields = decl.getitem(String(u"fields"))
            return ffi.Union(self.parse_fields(name, fields), name)
        if isinstance(which, String) and which.string == u"struct":
            fields = decl.getitem(String(u"fields"))
            return ffi.Struct(self.parse_fields(name, fields), name)
        if isinstance(which, String) and which.string == u"opaque":
            return ffi.Struct(None, name)
        raise Error(name + u": no ctype builder for " + which.repr())

    def parse_fields(self, name, fields_list):
        if not isinstance(fields_list, List):
            raise Error(name + u": ctype fields, expected list")
        fields = []
        for field in fields_list.contents:
            field_name = field.getitem(Integer(0))
            if not isinstance(field_name, String):
                raise Error(name + u": first column should be the name")
            ctype = self.lookup_type(field.getitem(Integer(1)))
            fields.append((field_name.string, ctype))
        return fields

def wrap_json(obj):
    if isinstance(obj, dict):
        dict_ = Dict()
        for key, value in obj.items():
            dict_.setitem(wrap_json(key), wrap_json(value))
        return dict_
    elif isinstance(obj, list):
        return List(map(wrap_json, obj))
    elif isinstance(obj, str):
        return from_cstring(obj)
    elif isinstance(obj, unicode):
        return from_ustring(obj)
    elif isinstance(obj, int):
        return Integer(obj)
    elif obj is None:
        return null
    else:
        assert False, repr(obj)

module = Module(u'api', {
}, frozen=True)

def builtin(fn):
    module.namespace[fn.__name__.decode('utf-8')] = Builtin(fn)
    return fn

@builtin
@signature(String)
def open(path):
    path = path.string
    if path.endswith(u".so"):
        path = path.rsplit(u'.', 1)[0]
    json_path = path + u".json"
    so_path = path + u".so"
    return ffi.Library.interface.call([String(so_path), open_api(json_path)])

def open_api(json_path):
    path = get_header(json_path)
    try:
        apispec = json.read_file(path)
    except OSError as error:
        raise Error(("[Errno %d]: %s\n" % (error.errno, path)).decode('utf-8'))
    api = Api(
        apispec.getitem(String(u"constants")),
        apispec.getitem(String(u"types")),
        apispec.getitem(String(u"variables")))
    return api
