import bon
import evaluator
import os
import space

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
    program = evaluator.loader.from_object(bon.open_file(cb_path))
    return program.call([module])

def compile_module(cb_path, src_path):
    pid = os.fork()
    if pid == 0:
        os.execv('compile.py', ["compile.py", cb_path, src_path])
        return
    pid, status = os.waitpid(pid, 0)
    if status != 0:
        raise space.Error(u"module compile failed: %s %s" % (cb_path.decode('utf-8'), src_path.decode('utf-8')))
