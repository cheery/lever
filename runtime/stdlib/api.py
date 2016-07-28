from rpython.translator.platform import platform
import pathobj
from space import *
import ffi
import json, os

class ApiConfig:
    def __init__(self):
        self.headers_dir = None

conf = ApiConfig()

def init(lever_path):
    conf.headers_dir = pathobj.concat(lever_path, pathobj.parse(u"headers"))

class Api(Object):
    def __init__(self, constants, types, variables, dependencies, decorator):
        self.cache = {}
        self.typecache = {}
        self.constants = constants
        self.types = types
        self.variables = variables
        self.dependencies = dependencies
        self.cycle_catch = {}
        self.decorator = decorator

    def getitem(self, name):
        if not isinstance(name, String):
            raise OldError(u"API.getitem requires a string")
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
                raise OldError(u"incorrect name record")
            if not isinstance(name, String):
                raise OldError(u"incorrect name record")
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
            if u"." in name.string and self.dependencies is not None:
                namespace, name = name.string.split(u".", 1)
                return self.dependencies.getitem(String(namespace)).getattr(name)
            raise unwind(LKeyError(self, name))
        else:
            return self.build_ctype(u"<unnamed>", name)

    def build_ctype(self, name, decl):
        if isinstance(decl, String):
            return self.lookup_type(decl)
        if self.decorator is not None:
            return ffi.to_type(self.decorator.call([self, String(name), decl]))
        else:
            return self.build_ctype_raw(name, decl)

    def build_ctype_raw(self, name, decl):
        which = decl.getitem(String(u"type"))
        if isinstance(which, String) and which.string == u"cfunc":
            restype = decl.getitem(String(u'restype'))
            argtypes_list = decl.getitem(String(u'argtypes'))
            if not isinstance(argtypes_list, List):
                raise OldError(u"incorrect function record")
            restype = self.lookup_type(restype)
            argtypes = []
            for argtype in argtypes_list.contents:
                argtypes.append(self.lookup_type(argtype))
            return ffi.CFunc(restype, argtypes)
        if isinstance(which, String) and which.string == u"union":
            if decl in self.cycle_catch:
                return self.cycle_catch[decl]
            fields = decl.getitem(String(u"fields"))
            self.cycle_catch[decl] = ctype = ffi.Union(None, name)
            ctype.declare(self.parse_fields(name, fields))
            return ctype
        if isinstance(which, String) and which.string == u"struct":
            if decl in self.cycle_catch:
                return self.cycle_catch[decl]
            fields = decl.getitem(String(u"fields"))
            self.cycle_catch[decl] = ctype = ffi.Struct(None, name)
            ctype.declare(self.parse_fields(name, fields))
            return ctype
        if isinstance(which, String) and which.string == u"opaque":
            return ffi.Struct(None, name)
        if isinstance(which, String) and which.string == u"array":
            ctype = self.lookup_type(decl.getitem(String(u'ctype')))
            length = decl.getitem(String(u"length"))
            if length is null:
                return ffi.Array(ctype)
            elif isinstance(length, Integer):
                return ffi.Array(ctype, length.value)
            else:
                raise OldError(name + u": incorrect length value: %s" % length.repr())
        if isinstance(which, String) and which.string == u"pointer":
            to_obj = decl.getitem(String(u'to'))
            # A little hack to name common opaque pointers.
            if isinstance(to_obj, Dict):
                to = self.build_ctype(name, to_obj)
            else:
                to = self.lookup_type(to_obj)
            return ffi.Pointer(to)
        if isinstance(which, String) and which.string == u"enum":
            ctype = self.lookup_type(decl.getitem(String(u'ctype')))
            constants = decl.getitem(String(u"constants"))
            if not isinstance(constants, Dict):
                raise unwind(LTypeError(name + u": expected constant table to be dictionary"))
            table = {}
            for name_, const in constants.data.iteritems():
                if not isinstance(name_, String):
                    raise unwind(LTypeError(name + u": expected constants table key to be string"))
                if not isinstance(const, Integer):
                    raise unwind(LTypeError(name + u": expected constants table value to be integer"))
                table[name_.string] = const.value
            return ffi.Bitmask(ffi.to_type(ctype), table, multichoice=False)
        if isinstance(which, String) and which.string == u"bitmask":
            ctype = self.lookup_type(decl.getitem(String(u'ctype')))
            constants = decl.getitem(String(u"constants"))
            if not isinstance(constants, Dict):
                raise unwind(LTypeError(name + u": expected constant table to be dictionary"))
            table = {}
            for name_, const in constants.data.iteritems():
                if not isinstance(name_, String):
                    raise unwind(LTypeError(name + u": expected constants table key to be string"))
                if not isinstance(const, Integer):
                    raise unwind(LTypeError(name + u": expected constants table value to be integer"))
                table[name_.string] = const.value
            return ffi.Bitmask(ffi.to_type(ctype), table, multichoice=True)
        raise OldError(name + u": no ctype builder for " + which.repr())

    def parse_fields(self, name, fields_list):
        if not isinstance(fields_list, List):
            raise OldError(name + u": ctype fields, expected list")
        fields = []
        for field in fields_list.contents:
            field_name = field.getitem(Integer(0))
            if not isinstance(field_name, String):
                raise OldError(name + u": first column should be the name")
            ctype = self.lookup_type(field.getitem(Integer(1)))
            fields.append((field_name.string, ctype))
        return fields

# I'm not sure how this method should be called.
@Api.method(u"build_type", signature(Api, String, Object))
def api_build_type(api, name, obj):
    return api.build_ctype_raw(name.string, obj)

@Api.method(u"lookup_type", signature(Api, Object))
def api_lookup_type(api, obj):
    return api.lookup_type(obj)

class FuncLibrary(Object):
    def __init__(self, api, func):
        self.func = func
        self.api = api
        self.namespace = {}

    def getattr(self, name):
        if name in self.namespace:
            return self.namespace[name]
        c = self.api.getitem(String(name))
        if isinstance(c, ffi.Wrap):
            cname = c.cname
            ctype = c.ctype
        else:
            return c
        res = self.func.call([String(cname)])
        if isinstance(res, ffi.Mem):
            return ffi.Mem(ctype, res.pointer, 1)
        elif res is null:
            raise unwind(LAttributeError(self, name))
        else:
            raise unwind(LTypeError(
                u"expected api(%s) is memory object, got %s" % (
                    cname, res.repr())))

@FuncLibrary.instantiator
@signature(Object, Object)
def _(api, func):
    return FuncLibrary(api, func)

module = Module(u'api', {
    u"so_ext": from_cstring(platform.so_ext),
    u"funclibrary": FuncLibrary.interface,
}, frozen=True)

def builtin(name, deco):
    def _builtin_(fn):
        module.setattr_force(name, Builtin(deco(fn)))
        return fn
    return _builtin_

@builtin(u"open", signature(String, Object, Object, Object, optional=3))
def open(path, func, dependencies, decorator):
    print "api.open will be soon removed in favor to api.open_nobind"
    print "Fix code using api.open(...) to use api.library(...)"
    return library(path, func, dependencies, decorator)

@builtin(u"library", signature(String, Object, Object, Object, optional=3))
def library(path, func, dependencies, decorator):
    path = path.string
    if path.endswith(u".so") or path.endswith(u".json") or path.endswith(u".dll"):
        path = path.rsplit(u'.', 1)[0]
    json_path = pathobj.parse(path + u".json")
    so_path = path + u"." + platform.so_ext.decode('utf-8')
    api = read_file(json_path, dependencies, decorator)
    if func is not None:
        return FuncLibrary(api, func)
    return ffi.Library.interface.call([String(so_path), api])

@builtin(u"open_nobind", signature(Object, Object, Object, optional=1))
def open_nobind(path, dependencies, decorator):
    print "api.open_nobind will be removed in favor to api.read_file"
    print "Fix code using api.open_nobind(...) to use api.read_file(...)"
    return read_file(path, dependencies, decorator)

@builtin(u"read_file", signature(pathobj.Path, Object, Object, optional=2))
def read_file(path, dependencies, decorator):
    basename = path.getattr(u"basename")
    if isinstance(basename, String):
        if not basename.string.endswith(u".json"):
            path.setattr(
                u"basename",
                String(basename.string + u".json"))
    path = pathobj.concat(conf.headers_dir, path)
    try:
        apispec = json.read_file([path])
    except OSError as error:
        raise OldError(u"[Errno %d]: %s\n" % (error.errno, pathobj.stringify(path)))
    return read_object(apispec, dependencies, decorator)

@builtin(u"read_object", signature(Object, Object, Object, optional=2))
def read_object(apispec, dependencies, decorator):
    return Api(
        apispec.getitem(String(u"constants")),
        apispec.getitem(String(u"types")),
        apispec.getitem(String(u"variables")),
        dependencies,
        decorator)
