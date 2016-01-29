import bon
import evaluator
import os
import space
import sys
import main
import pathobj

def start(main_script, main_module):
    assert isinstance(main_script, space.String)
    script_dir = pathobj.concat(pathobj.getcwd(), pathobj.os_parse(main_script.string))
    name = script_dir.getattr(u"basename")
    #This is bit of work in progress.
    if isinstance(name, space.String) and name.string.endswith(".lc"):
        L = len(name.string) - 3
        if L >= 0:
            name = space.String(name.string[0:L])
    main_module.setattr(u"name", name)
    script_dir.setattr(u"basename", space.String(u""))
    main_module.setattr(u"dir", script_dir)
    #ec = main.get_ec()
    s = main_script.string.encode('utf-8')
    return load_module(s, main_module)

# plans: implement import -object here.
#        have import.scope -object that takes care about how import can behave.
#        allow modules derive or create new scopes and isolate themselves.
# import resolution:
#  local/script.lc
#  scope/
#  $LEVER_PATH/lib/
#  global

def load_module(src_path, module):
    cb_path = src_path + '.cb'
    cb_present = os.path.exists(cb_path)
    cb_compile = True
    cb_mtime = 0.0
    if cb_present:
        cb_stat = os.stat(cb_path)
        cb_compile = (cb_stat.st_mode & 0o444) > 0
        cb_mtime = cb_stat.st_mtime
    if cb_compile:
        src_present = os.path.exists(src_path)
        if src_present:
            src_stat = os.stat(src_path)
        else:
            raise space.Error(u"module '%s' not present" % src_path.decode('utf-8'))
        if cb_present: 
            cb_present = not cb_mtime < src_stat.st_mtime
        if not cb_present:
            compile_module(cb_path, src_path)
    program = evaluator.loader.from_object(bon.open_file(pathobj.os_parse(cb_path.decode('utf-8'))))
    return program.call([module])

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
            raise space.Error(u"module compile failed: %s %s" % (cb_path.decode('utf-8'), src_path.decode('utf-8')))
else:
    def compile_module(cb_path, src_path):
        app_dir = os.environ.get('LEVER_PATH')
        if app_dir is None:
            app_dir = ''
        compiler_path = os.path.join(app_dir, "compile.py")
        py_path = find_python_interpreter()
        status = os.spawnv(os.P_WAIT, py_path, [py_path, escape_arg(compiler_path), escape_arg(cb_path), escape_arg(src_path)])
        if status != 0:
            raise space.Error(u"module compile failed: %s %s" % (cb_path.decode('utf-8'), src_path.decode('utf-8')))

    def find_python_interpreter():
        pths = os.environ.get("PATH").split(";")
        for p in pths:
            k = os.path.join(p, "python.exe")
            if os.path.exists(k):
                return escape_arg(k)
        return "python.exe" 

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
