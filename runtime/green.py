from rpython.config.translationoption import get_combined_translation_config
from rpython.rlib.rtimer import read_timestamp
from rpython.rlib.objectmodel import we_are_translated
from rpython.rlib.rstacklet import StackletThread
from space import *
import base

class ProcessState:
    def clear(self):
        self.stacklet = None
        self.current = None
        self.topmost = None

        self.origin = None
        self.destination = None
process = ProcessState()
process.clear()

def init(config):
    process.stacklet = StackletThread(config)
    process.current = Greenlet(
        process.stacklet.get_null_handle(),
        True)
    process.topmost = process.current
    process.origin = None
    process.destination = None

class Greenlet(Object):
    def __init__(self, handle, initialized, argv=None):
        self.handle = handle
        self.initialized = initialized
        self.argv = argv
        self.parent = process.current
        self.error = None

    def getattr(self, name):
        if name == u'parent':
            return self.parent or null
        return Object.getattr(self, name)

    def repr(self):
        return u"<greenlet>"

def switch(argv):
    destination = argv.pop(0)
    assert isinstance(destination, Greenlet)
    process.origin = process.current
    process.destination = destination
    if process.origin == process.destination:
        if len(argv) == 0:
            return null
        else:
            return argv[0]
    elif not process.destination.initialized:
        process.destination.argv += argv
        process.destination.initialized = True
        h = process.stacklet.new(greenlet_init)
        #h = process.stacklet.switch(process.destination.handle)
    else:
        if process.stacklet.is_empty_handle(process.destination.handle):
            raise Error(u"dead greenlet")
        process.destination.argv = argv
        h = process.stacklet.switch(process.destination.handle)
    process.destination.handle = process.origin.handle
    process.origin.handle = h
    process.current = process.destination
    process.origin = None
    process.destination = None

    assert process.current is not None
    if process.current.error is not None:
        raise process.current.error
    assert process.current.argv is not None
    if len(process.current.argv) == 0:
        retval = null
    else:
        retval = process.current.argv[0]
    process.current.argv = None
    return retval

Greenlet.interface.methods[u'switch'] = Builtin(switch)

def greenlet_init(head, arg):
    process.origin.handle = head
    # fill greenlet's handle
    #handle = process.stacklet.switch(head)
    #process.origin.handle = handle

    process.current = process.destination
    process.origin = None
    process.destination = None

    func = process.current.argv.pop(0)
    try:
        argv = [func.call(process.current.argv)]
        error = None
    except Error as error:
        argv = None

    parent = process.current.parent
    while process.stacklet.is_empty_handle(parent.handle):
        parent = parent.parent
    parent.argv = argv
    parent.error = error
    process.origin = process.current
    process.destination = parent
    return parent.handle

@base.builtin
def getcurrent(argv):
    return process.current

@base.builtin
def greenlet(argv):
    return Greenlet(process.current.handle, False, argv)
