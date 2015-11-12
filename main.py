from rpython.config.translationoption import get_combined_translation_config
from rpython.rlib.objectmodel import we_are_translated
from util import STDIN, STDOUT, STDERR, read_file, write
from runtime.stdlib import api
from runtime import base
import evaluator.loader
import space
import sys, os
config = get_combined_translation_config(translating=True)
#if not we_are_translated():
#    config.translation.continuation = True
if config.translation.continuation:
    from runtime import green


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

#def interactive():
#    module = space.Module(u'shell', {}, extends=base.module)
#    prompt = u"pyl> "
#    write(STDOUT, prompt)
#    source = os.read(0, 4096).decode('utf-8')
#    while source != u"":
#        try:
#            program = to_program(read(source))
#            write(STDOUT, program.call([module]).repr() + u"\n")
#        except space.Error as error:
#            print_traceback(error)
#        write(STDOUT, prompt)
#        source = os.read(0, 4096).decode('utf-8')
#    if source == u"":
#        write(STDOUT, u"\n")
#    return 0
#
#def batch(path):
#    module = space.Module(u'main', {}, extends=base.module)
#    try:
#        source = read_file(path)
#    except OSError, error:
#        os.write(2, "[Errno %d]: %s\n" % (error.errno, path) )
#        return 1
#    try:
#        program = to_program(read(source))
#        program.call([module])
#    except space.Error as error:
#        print_traceback(error)
#        return 1
#    return 0

#def entry_point(argv):
#    E = 10 # Debugging assist
#    green.process.init(config)
#    api.init(argv)
#    if len(argv) <= 1:
#        return interactive()
#    for arg in argv[1:]:
#        if arg == '-E0':
#            E = 0
#        elif arg == '-E1':
#            E = 1
#        elif arg == '-E2':
#            E = 2
#        elif E == 0:
#            # At this option, we're just parsing the input.
#            try:
#                source = read_file(arg)
#            except OSError, error:
#                os.write(2, "[Errno %d]: %s\n" % (error.errno, arg) )
#                return 1
#            for exp in read(source):
#                write(STDOUT, exp.repr() + u"\n")
#        else:
#            status = batch(arg)
#            if status != 0:
#                return status
#    return 0

import bon

def entry_point(argv):
    if config.translation.continuation:
        green.process.init(config)
    api.init(argv)
    try:
        for arg in argv[1:]:
            module = space.Module(u'main', {}, extends=base.module)
            result = load_module(arg, module)
            os.write(1, (result.repr() + u'\n').encode('utf-8'))
    except space.Error as error:
        print_traceback(error)
        return 1
    return 0

def print_traceback(error):
    out = u""
    if len(error.stacktrace) > 0:
        out = u"Traceback:\n"
    for frame, start, stop in reversed(error.stacktrace):
        out += u"    %s: %s %s\n" % (
            frame.module.name, start.repr(), stop.repr())
    out += error.__class__.__name__.decode('utf-8')
    write(STDERR, out + u": " + error.message + u"\n")

def target(*args):
    return entry_point, None

def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__=='__main__':
    sys.exit(entry_point(sys.argv))
