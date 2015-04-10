from compiler import to_program
from reader import read, Literal, Expr
from rpython.config.translationoption import get_combined_translation_config
import base
import space
import sys, os
config = get_combined_translation_config(translating=True)
config.translation.continuation = True

import green

STDIN = 0
STDOUT = 1
STDERR = 2

def interactive():
    module = space.Module(u'shell', {}, extends=base.module)
    prompt = u"pyl> "
    write(STDOUT, prompt)
    source = os.read(0, 4096).decode('utf-8')
    while source != u"":
        try:
            program = to_program(read(source))
            write(STDOUT, program.call([module]).repr() + u"\n")
        except space.Error as error:
            print_traceback(error)
        write(STDOUT, prompt)
        source = os.read(0, 4096).decode('utf-8')
    if source == u"":
        write(STDOUT, u"\n")
    return 0

def batch(path):
    module = space.Module(u'main', {}, extends=base.module)
    try:
        source = read_file(path)
    except OSError, error:
        os.write(2, str(error))
        return 1
    try:
        program = to_program(read(source))
        program.call([module])
    except space.Error as error:
        print_traceback(error)
        return 1
    return 0

def entry_point(argv):
    green.process.init(config)
    if len(argv) <= 1:
        return interactive()
    for arg in argv[1:]:
        status = batch(arg)
        if status != 0:
            return status
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

def read_file(path):
    fd = os.open(path, os.O_RDONLY, 0777)
    try:
        data = ""
        frame = os.read(fd, 4096)
        while frame != "":
            data += frame
            frame = os.read(fd, 4096)
    finally:
        os.close(fd)
    return data.decode('utf-8')

def write(fd, message):
    assert isinstance(message, unicode)
    os.write(fd, message.encode('utf-8'))

def target(*args):
    return entry_point, None

if __name__=='__main__':
    sys.exit(entry_point(sys.argv))
