from rpython.config.translationoption import get_combined_translation_config
from rpython.rlib.objectmodel import we_are_translated
from runtime.util import STDIN, STDOUT, STDERR, read_file, write
from runtime.stdlib import api
from runtime import base, eventloop
import bon
import evaluator.loader
import space
import sys, os
config = get_combined_translation_config(translating=True)
if not we_are_translated():
    config.translation.continuation = True
if config.translation.continuation:
    from runtime import green

from runtime import module_resolution

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

def entry_point(argv_raw):
    if config.translation.continuation:
        green.init(config)
    eventloop.init()
    api.init(argv_raw)
    argv = [system_init]
    for arg in argv_raw[1:]:
        argv.append(space.String(arg.decode('utf-8')))
    eventloop.state.queue.append(argv)
    try:
        eventloop.run()
    except space.Error as error:
        print_traceback(error)
        return 1
    return 0

@space.Builtin
def system_init(argv):
    module_src = argv[0]
    assert isinstance(module_src, space.String)
    module = space.Module(u'main', {}, extends=base.module)
    result = module_resolution.load_module(module_src.string.encode('utf-8'), module)
    try:
        main_func = module.getattr(u"main")
    except space.Error as error:
        pass
    else:
        result = main_func.call([space.List(argv)])
    return space.null

def print_traceback(error):
    out = u""
    if len(error.stacktrace) > 0:
        out = u"\033[31mTraceback:\033[36m\n"
    for pc, constants, sourcemap in reversed(error.stacktrace):
        name, col0, lno0, col1, lno1 = pc_location(pc, constants, sourcemap)
        out += u"    %s: %d,%d : %d,%d\n" % (name.repr(), lno0, col0, lno1, col1)
    out += u"\033[31mError:\033[0m"
    write(STDERR, out + u" " + error.message + u"\n")

def pc_location(pc, constants, sourcemap):
    if not isinstance(sourcemap, space.List):
        return space.String(u"<no sourcemap>"), 0, 0, -1, -1
    for cell in sourcemap.contents:
        count = sourcemap_getitem_int(cell, 0)
        if pc <= count:
            const = sourcemap_getitem_int(cell, 1)
            col0 = sourcemap_getitem_int(cell, 2)
            lno0 = sourcemap_getitem_int(cell, 3)
            col1 = sourcemap_getitem_int(cell, 4)
            lno1 = sourcemap_getitem_int(cell, 5)
            return constants[const], col0, lno0, col1, lno1
        else:
            pc -= count
    return space.String(u"<over sourcemap>"), 0, 0, -1, -1

def sourcemap_getitem_int(cell, index):
    item = cell.getitem(space.Integer(index))
    if isinstance(item, space.Integer):
        return item.value
    raise space.Error(u"invalid sourcemap format")

def target(*args):
    return entry_point, None

def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__=='__main__':
    sys.exit(entry_point(sys.argv))
