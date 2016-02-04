from space import *
import base
import bon
import evaluator
import main
import os
import pathobj
import stdlib
import sys

# Module namespace.
builtin_modules = {}
for py_module in stdlib.import_all_modules():
    builtin_modules[py_module.module.name] = py_module.module

# TODO: enclose "lib_modules" inside Importer
lib_modules = {}

def start(main_script, main_module):
    assert isinstance(main_script, String)
    main_path = pathobj.os_parse(resuffix(main_script.string, u".lc", u""))
    return load(main_path, main_module)

# plans: 
#        have import.scope -object that takes care about how import can behave.
#        allow modules derive or create new scopes and isolate themselves.

def exists(module_path):
    s = pathobj.os_stringify(module_path).encode('utf-8')
    if os.path.isdir(s):
        w = os.path.join(s, "init")
        if os.path.exists(w + ".lc.cb"):
            return True
        if os.path.exists(w + ".lc"):
            return True
    if os.path.exists(s + ".lc.cb"):
        return True
    if os.path.exists(s + ".lc"):
        return True
    return False

def load(module_path, module):
    module_path = pathobj.concat(pathobj.getcwd(), module_path)
    s = pathobj.os_stringify(module_path).encode('utf-8')
    is_dir = False
    if os.path.isdir(s):
        w = os.path.join(s, "init")
        if os.path.exists(w + ".lc.cb") or os.path.exists(w + ".lc"):
            is_dir = True
            s = w
    cb_path = s + ".lc.cb"
    cb_present = os.path.exists(cb_path)
    cb_mtime = 0.0
    if cb_present:
        cb_stat = os.stat(s + ".lc.cb")
        cb_mtime = cb_stat.st_mtime
    lc_path = s + ".lc"
    lc_present = os.path.exists(lc_path)
    if lc_present:
        lc_stat = os.stat(lc_path)
        if cb_present:
            cb_present = not cb_mtime < lc_stat.st_mtime
        if not cb_present:
            compile_module(cb_path, lc_path)
    program = evaluator.loader.from_object(bon.open_file(pathobj.os_parse(cb_path.decode('utf-8'))))
    module_path.drop_slash()
    name = module_path.getattr(u"basename")
    if not is_dir:
        module_path.setattr(u"basename", String(u""))
    module.setattr(u"dir", module_path)
    module.setattr(u"name", name)
    module.setattr(u"import", Import(module_path))
    return program.call([module])

class Import(Object):
    def __init__(self, local):
        self.local = local

    def call(self, argv):
        if len(argv) != 1:
            raise Error(u"wrong number of arguments to import")
        name = argv[0]
        if isinstance(name, pathobj.Path):
            raise Error(u"no direct loading yet")
        elif not isinstance(name, String):
            raise Error(u"expected string")
        # import resolution:
        #  local/script.lc
        local_path = pathobj.concat(self.local, pathobj.to_path(name))
        if exists(local_path):
            # TODO: implement module caching
            this = Module(name.string, {}, extends=base.module) # base.module
            load(local_path, this)
            return this
        #  scope/
        # TODO: implement scope?
        #  $LEVER_PATH/lib/
        if name.string in lib_modules:
            return lib_modules[name.string]
        lib_path = pathobj.concat(main.get_ec().lever_path, pathobj.parse(u"lib"))
        lib_path = pathobj.concat(lib_path, pathobj.to_path(name))
        if exists(lib_path):
            # TODO: improve module caching
            this = Module(name.string, {}, extends=base.module) # base.module
            load(lib_path, this)
            lib_modules[name.string] = this
            return this
        #  global
        if name.string in builtin_modules:
            return builtin_modules[name.string]
        raise Error(u"module '%s' not present" % name.string)

if sys.platform != "win32":
    # we have some expectations from non-windows platforms.
    # the expectation is that they hesitate to suck for sake of just being different.
    def compile_module(cb_path, src_path):
        app_dir = os.environ.get('LEVER_PATH')
        if app_dir is None:
            app_dir = ''
        compiler_path = os.path.join(app_dir, "compile.py")
        pid = os.fork()
        if pid == 0:
            os.execv(compiler_path, [compiler_path, cb_path, src_path])
            return
        pid, status = os.waitpid(pid, 0)
        if status != 0:
            raise Error(u"module compile failed: %s %s" % (cb_path.decode('utf-8'), src_path.decode('utf-8')))
else:
    def compile_module(cb_path, src_path):
        app_dir = os.environ.get('LEVER_PATH')
        if app_dir is None:
            app_dir = ''
        compiler_path = os.path.join(app_dir, "compile.py")
        py_path = find_python_interpreter()
        status = os.spawnv(os.P_WAIT, py_path, [py_path, escape_arg(compiler_path), escape_arg(cb_path), escape_arg(src_path)])
        if status != 0:
            raise Error(u"module compile failed: %s %s" % (cb_path.decode('utf-8'), src_path.decode('utf-8')))

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
