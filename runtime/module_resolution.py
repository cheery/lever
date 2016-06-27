from space import *
import base
import bon
import evaluator
import main
import os
import pathobj
import stdlib
import sys

class ModuleScope(Object):
    def __init__(self, local, parent=None, frozen=False):
        self.cache = {} # maps absolute path -> module cache entry
        self.local = local
        self.parent = parent
        self.frozen = frozen # if frozen, the scope relies on cache.

    def setcache(self, m_path, module, mtime):
        m = ModuleCache(m_path, module, mtime)
        self.cache[pathobj.stringify(m_path)] = m
        return m

    def getcache(self, m_path):
        s = pathobj.stringify(m_path)
        try:
            return self.cache[s]
        except KeyError as k:
            return None

    def getitem(self, item):
        if isinstance(item, String):
            if item.string in self.cache:
                return self.cache[item.string]
        raise OldError(u"%s not in module scope" % item.repr())

    def iter(self):
        return ScopeIterator(self.cache.iterkeys())

class ScopeIterator(Object):
    _immutable_fields_ = ['iterator']
    def __init__(self, iterator):
        self.iterator = iterator

    def iter(self):
        return self

@ScopeIterator.builtin_method
@signature(ScopeIterator)
def next(self):
    return String(self.iterator.next())

class ModuleCache(Object):
    def __init__(self, path, module, mtime):
        self.path = path
        self.module = module
        self.mtime = mtime

    def getattr(self, name):
        if name == u"path":
            return self.path
        if name == u"module":
            return self.module
        if name == u"mtime":
            return Float(self.mtime)
        return Object.getattr(self, name)

@ModuleCache.builtin_method
@signature(ModuleCache)
def get_moduleinfo(self):
    return moduleinfo(self.path)

root_module = ModuleScope(pathobj.parse(u"builtin:/"), frozen=True)
for py_module in stdlib.import_all_modules():
    p = pathobj.concat(root_module.local, pathobj.parse(py_module.module.name))
    root_module.setcache(p, py_module.module, 0.0)

def start(main_script):
    assert isinstance(main_script, String)
    lib_scope = ModuleScope(
        pathobj.concat(main.get_ec().lever_path, pathobj.parse(u"lib")),
        root_module)
    main_path = pathobj.os_parse(resuffix(main_script.string, u".lc", u""))
    mi = moduleinfo(pathobj.abspath(main_path))
    scope = ModuleScope(mi.directory, lib_scope)
    this = Module(mi.name.string, {}, extends=base.module) # base.module
    if not (mi.lc_present or mi.cb_present):
        raise OldError(u"main module not present")
    mi.default_config(this, scope)
    mi.loadit(this)
    scope.setcache(main_path, this, max(mi.lc_mtime, mi.cb_mtime))
    return this

# plans: 
#        allow modules derive or create new scopes and isolate themselves.

# module path 
def moduleinfo(module_path):
    module_path = pathobj.abspath(module_path)
    module_name = module_path.getattr(u"basename")
    assert isinstance(module_name, String)
    s = pathobj.os_stringify(module_path).encode('utf-8')
    is_dir = False
    if os.path.isdir(s):
        w = os.path.join(s, "init")
        if os.path.exists(w + ".lc.cb") or os.path.exists(w + ".lc"):
            is_dir = True
            s = w
    else:
        module_path = pathobj.directory(module_path)
    cb_path = s + ".lc.cb"
    cb_present = os.path.exists(cb_path)
    cb_mtime = 0.0
    lc_path = s + ".lc"
    lc_present = os.path.exists(lc_path)
    lc_mtime = 0.0
    if cb_present:
        cb_mtime = os.path.getmtime(cb_path)
    if lc_present:
        lc_mtime = os.path.getmtime(lc_path)
    # This ignores outdated bytecode objects.
    if cb_present and lc_present:
        cb_present = not cb_mtime < lc_mtime
    return ModuleInfo(
        module_name, module_path,
        pathobj.os_parse(cb_path.decode('utf-8')), cb_present, cb_mtime,
        pathobj.os_parse(lc_path.decode('utf-8')), lc_present, lc_mtime,
    )

class ModuleInfo(Object):
    def __init__(self, name, directory, cb_path, cb_present, cb_mtime, lc_path, lc_present, lc_mtime):
        self.name = name
        self.directory = directory
        self.cb_path    = cb_path
        self.cb_present = cb_present
        self.cb_mtime   = cb_mtime
        self.lc_path    = lc_path
        self.lc_present = lc_present
        self.lc_mtime   = lc_mtime

    def default_config(self, module, scope):
        module.setattr(u"dir", self.directory)
        module.setattr(u"name", self.name)
        module.setattr(u"import", Import(self.directory, scope))
        return module

    def loadit(self, module):
        if not self.cb_present:
            compile_module(self.cb_path, self.lc_path)
            self.cb_mtime = os.path.getmtime(pathobj.os_stringify(self.cb_path).encode('utf-8'))
            self.cb_present = True
        program = evaluator.loader.from_object(bon.open_file(self.cb_path))
        return program.call([module])

    def getattr(self, name):
        if name == u"present":
            return boolean(self.cb_present or self.lc_present)
        if name == u"mtime":
            return Float(max(self.lc_mtime, self.cb_mtime))
        return Object.getattr(self, name)

class Import(Object):
    def __init__(self, local, scope):
        self.local = local
        self.scope = scope

    def call(self, argv):
        if len(argv) != 1:
            raise OldError(u"wrong number of arguments to import")
        name = argv[0]
        if isinstance(name, pathobj.Path):
            raise OldError(u"no direct loading yet")
        elif not isinstance(name, String):
            raise OldError(u"expected string")
        # import resolution:
        #  local/script.lc
        path = pathobj.concat(self.local, pathobj.to_path(name))
        cache = self.scope.getcache(path)
        if cache:
            return cache.module
        if not self.scope.frozen:
            mi = moduleinfo(path)
            if mi.lc_present or mi.cb_present:
                this = Module(name.string, {}, extends=base.module) # base.module
                mi.default_config(this, self.scope)
                mi.loadit(this)
                self.scope.setcache(path, this, max(mi.lc_mtime, mi.cb_mtime))
                return this
        # scope/
        scope = self.scope
        while scope is not None:
            path = pathobj.concat(scope.local, pathobj.to_path(name))
            cache = scope.getcache(path)
            if cache:
                return cache.module
            if not scope.frozen:
                mi = moduleinfo(path)
                if mi.lc_present or mi.cb_present:
                    this = Module(name.string, {}, extends=base.module) # base.module
                    mi.default_config(this, scope)
                    mi.loadit(this)
                    scope.setcache(path, this, max(mi.lc_mtime, mi.cb_mtime))
                    return this
            scope = scope.parent
        raise OldError(u"module '%s' not present" % name.string)

    def getattr(self, name):
        if name == u'scope':
            return self.scope
        return Object.getattr(self, name)

@ModuleScope.builtin_method
@signature(ModuleScope, String)
def reimport(scope, obj):
    if obj.string not in scope.cache:
        raise OldError(u"Cannot reimport, module not present")
    mc = scope.cache[obj.string]
    mi = moduleinfo(mc.path)
    mi.default_config(mc.module, scope)
    mi.loadit(mc.module)
    mc.mtime = max(mi.lc_mtime, mi.cb_mtime)
    return mc.module

if sys.platform != "win32":
    # we have some expectations from non-windows platforms.
    # the expectation is that they hesitate to suck for sake of just being different.
    def compile_module(cb_path, src_path):
        cb_path = pathobj.os_stringify(cb_path).encode('utf-8')
        src_path = pathobj.os_stringify(src_path).encode('utf-8')
        app_dir = os.environ.get('LEVER_PATH')
        if app_dir is None:
            app_dir = ''
        compiler_path = os.path.join(app_dir, "compiler/compile.py")
        pid = os.fork()
        if pid == 0:
            os.execv(compiler_path, [compiler_path, cb_path, src_path])
            return
        pid, status = os.waitpid(pid, 0)
        if status != 0:
            raise OldError(u"module compile failed: %s %s" % (cb_path.decode('utf-8'), src_path.decode('utf-8')))
else:
    def compile_module(cb_path, src_path):
        cb_path = pathobj.os_stringify(cb_path).encode('utf-8')
        src_path = pathobj.os_stringify(src_path).encode('utf-8')
        app_dir = os.environ.get('LEVER_PATH')
        if app_dir is None:
            app_dir = ''
        compiler_path = os.path.join(app_dir, "compiler/compile.py")
        py_path = find_python_interpreter()
        status = os.spawnv(os.P_WAIT, py_path, [py_path, escape_arg(compiler_path), escape_arg(cb_path), escape_arg(src_path)])
        if status != 0:
            raise OldError(u"module compile failed: %s %s" % (cb_path.decode('utf-8'), src_path.decode('utf-8')))

    def find_python_interpreter():
        pths = os.environ.get("PATH").split(";")
        for p in pths:
            k = os.path.join(p, "python.exe")
            if os.path.exists(k):
                return escape_arg(k)
        return r"C:\Python27\python.exe" 

    def escape_arg(arg):
        result = []
        bs_buf = []
        # Add a space to separate this argument from the others
        needquote = (" " in arg) or ("\t" in arg) or not arg
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backslashes.
                result.append('\\' * len(bs_buf)*2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backslashes, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')
        return ''.join(result)

def resuffix(string, suffix, new_suffix=u""):
    if string.endswith(suffix):
        i = max(0, len(string) - len(suffix))
        return string[0:i] + new_suffix
    return string + new_suffix
