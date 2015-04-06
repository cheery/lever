# These came here, I'll provide them when it's appropriate again.

#from rpython.config.translationoption import get_combined_translation_config
#from rpython.rlib.rtimer import read_timestamp
#from rpython.rlib.objectmodel import we_are_translated
#
#if config.translation.continuation:
#    from rpython.rlib.rstacklet import StackletThread

#class GlobalState:
#    stacklet = None
#    current = None # The current greenlet
#
#class Greenlet(Object):
#    def __init__(self, handle, initialized, argv=None):
#        self.handle = handle
#        self.initialized = initialized
#        self.argv = argv
#        self.parent = process.current
#        self.callee = None
#
#    def switch(self, argv):
#        if not self.initialized:
#            self.argv += argv
#            self.initialized = True
#            self.callee = process.current
#            process.current = self
#            self.handle = process.stacklet.new(greenlet_init)
#            callee = process.stacklet.switch(self.handle)
#            process.current.callee.handle = callee
#        else:
#            if process.stacklet.is_empty_handle(self.handle):
#                raise Exception("dead greenlet")
#            self.argv = argv
#            self.callee = process.current
#            process.current = self
#            callee = process.stacklet.switch(self.handle)
#            process.current.callee.handle = callee
#        if len(process.current.argv) == 0:
#            retval = null
#        else:
#            retval = process.current.argv[0]
#        process.current.argv = None
#        return retval
#
#    def getattr(self, name):
#        if name == 'switch':
#            return GreenletSwitch(self)
#        if name == 'parent':
#            return self.parent or null
#        return Object.getattr(self, name)
#
#    def repr(self):
#        return "<greenlet " + str(self.handle) + ">"
#
#class GreenletSwitch(Object):
#    def __init__(self, greenlet):
#        self.greenlet = greenlet
#
#    def invoke(self, argv):
#        return self.greenlet.switch(argv)
#
#    def repr(self):
#        return self.greenlet.repr() + ".switch"
#
#def greenlet_init(head, arg):
#    # fill greenlet's handle.
#    callee = process.stacklet.switch(head)
#    process.current.callee.handle = callee
#    current = process.current
#
#    func = current.argv.pop(0)
#    retval = func.invoke(current.argv)
#
#    parent = process.current.parent
#    while process.stacklet.is_empty_handle(parent.handle):
#        parent = parent.parent
#    parent.argv = [retval]
#    parent.callee = process.current
#    process.current = parent
#    return parent.handle
#
#process = GlobalState()
#
#def pyl_getcurrent(argv):
#    return process.current
#
#def pyl_greenlet(argv):
#    return Greenlet(process.current.handle, False, argv)
#
#if config.translation.continuation:
#    global_scope.update({
#        "getcurrent": BuiltinFunction(pyl_getcurrent, "getcurrent"),
#        "greenlet": BuiltinFunction(pyl_greenlet, "greenlet"),
#    })
#
#from greenlet import getcurrent, greenlet
#class StackletThreadShim:
#    def __init__(self, config):
#        self.config = config
#        self.null_handle = getcurrent()
#
#    def get_null_handle(self):
#        return self.null_handle
#
#    def new(self, callback):
#        g = greenlet(callback)
#        return g.switch(getcurrent(), 0)
#
#    def switch(self, handle):
#        return handle.switch(getcurrent())
#
#    def is_empty_handle(self, handle):
#        return handle.dead
#
#def entry_point(argv):
#    if config.translation.continuation:
#        if we_are_translated():
#            process.stacklet = StackletThread(config)
#        else:
#            process.stacklet = StackletThreadShim(config)
#        process.current = Greenlet(process.stacklet.get_null_handle(), True)
