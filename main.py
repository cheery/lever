from rpython.rlib.objectmodel import we_are_translated, keepalive_until_here
from runtime.util import STDIN, STDOUT, STDERR, read_file, write
from runtime.stdlib import api
from runtime import base, eventloop
import bon
import evaluator.loader
import space
import sys, os


#from runtime import green
#from runtime import module_resolution
from runtime import main
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

#def entry_point(argv_raw):
#    sthread = StackletThread(config)
#    green.init(sthread)
#    eventloop.init()
#    api.init(argv_raw)
#    argv = [system_init]
#    for arg in argv_raw[1:]:
#        argv.append(space.String(arg.decode('utf-8')))
#    green.process.eventloop.queue.append(argv)
#    retcode = 0
#    try:
#        eventloop.run()
#    except space.Error as error:
#        print_traceback(error)
#        retcode = 1
#    keepalive_until_here(sthread)
#    return retcode

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

def target(*args):
    return main.entry_point, None

def jitpolicy(driver):
    from rpython.jit.codewriter.policy import JitPolicy
    return JitPolicy()

if __name__=='__main__':
    sys.exit(main.entry_point(sys.argv))
