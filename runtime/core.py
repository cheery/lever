# Rationale for this module comes from the dependency flow:
# main -> bunch of stuff -> core -> space, continuations

#from rpython.rlib.objectmodel import we_are_translated, keepalive_until_here
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
#from rpython.rlib.rthread import ThreadLocalReference
#from rpython.rlib import rgc
from continuations import Continuation
import rlibuv as uv
import space
import os

class ExecutionContext(object):
    #_immutable_fields_ = ['debug_hook?']
    def __init__(self, config, lever_path, uv_loop, uv_idler):
        self.config = config
        self.lever_path = lever_path
        self.sthread = None                 # Stacklets
        self.uv_loop = uv_loop
        self.uv_idler = uv_idler
        self.uv_closing = {}                # Handles about to close.
        self.uv_sleepers = {}               # Holds the sleeping greenlets.
        self.uv_readers = {}                # Reading streams.
        self.uv_writers = {}
        self.queue = []                     # Event queue.
        self.current = Greenlet(None, [])#, None)
        self.eventloop = self.current
        self.exit_status = 0
        # The newer and better handlers.
        # TODO: drop most of the old handlers to favor these.
        self.uv__read = {}
        self.uv__write = {}
        self.uv__connect = {}
        self.uv__udp_recv = {}
        self.uv__udp_send = {}
        self.uv__shutdown = {}
        self.uv__connection = {}
        self.uv__close = {}
        self.uv__poll = {}
        self.uv__timer = {}
        #self.uv__async = {}      # Dropped the ones
        #self.uv__prepare = {}    # I possibly won't need.
        #self.uv__check = {}
        #self.uv__idle = {}
        #self.uv__exit = {}
        #self.uv__walk = {}
        self.uv__fs = {}
        self.uv__fs_event = {}
        #self.uv__work = {}
        #self.uv__after_work = {}
        self.uv__getaddrinfo = {}
        self.uv__getnameinfo = {}
        #self.debug_hook = None

        # You can attach a queue to log stuff with a "register_logger(queue)"
        self.loggers = []

    def enqueue(self, task):
        if len(self.queue) == 0 and not uv.is_active(rffi.cast(uv.handle_ptr, self.uv_idler)):
            uv.idle_start(self.uv_idler, run_queued_tasks)
        self.queue.append(task)

    def log(self, which, obj):
        entry = space.Exnihilo()
        entry.setattr(u"type", space.String(which))
        entry.setattr(u"value", obj)
        for logger in list(self.loggers):
            if logger.closed:
                self.loggers.remove(logger)
            else:
                logger.append(entry)
        return len(self.loggers)

    def log_other(self, which, obj):
        if self.log(which, obj) == 0:
            fd = 2 if which != u"info" else 1
            if which == u"info" and isinstance(obj, space.List):
                sep = u''
                out = u""
                for arg in obj.contents:
                    if isinstance(arg, space.String):
                        string = arg.string
                    else:
                        string = arg.repr()
                    out += sep + string
                    sep = u' '
                obj = space.String(out)
            if isinstance(obj, space.String):
                os.write(fd, obj.string.encode('utf-8') + "\n")
            else:
                os.write(fd, obj.repr().encode('utf-8') + "\n")

    def log_exception(self, exception):
        if self.log(u"exception", exception) == 0:
            import base
            os.write(2, base.format_traceback_raw(exception).encode('utf-8') + "\n")

    def last_chance_logging(self):
        loggers, self.loggers = self.loggers, []
        # last chance logging
        # at this point it is best-effort.
        try:
            if len(loggers) > 0:
                for item in loggers[0].items:
                    which = item.getattr(u"type")
                    value = item.getattr(u"value")
                    which = space.cast(which, space.String, u"last_chance_logging")
                    if which.string != u"exception":
                        continue
                    self.log_exception(value)
        except space.Unwinder as unwinder:
            self.log_exception(unwinder.exception)

def run_queued_tasks(handle):
    ec = get_ec()
    queue, ec.queue = ec.queue, []
    for item in queue:
        root_switch(ec, [item])
    if len(ec.queue) == 0: # trick.
        uv.idle_stop(ec.uv_idler)

class GlobalState(object):
    ec = None

#global_state = ThreadLocalReference(GlobalState)
g = GlobalState()
def get_ec():
    return g.ec

def root_switch(ec, argv):
    try:
        switch(argv)
    except space.Unwinder as unwinder:
        ec.log_exception(unwinder.exception)

def root_unwind(ec, unwinder):
    ec.log_exception(unwinder.exception)

def schedule(argv):
    ec = get_ec()
    c = to_greenlet(argv)
    ec.enqueue(c)
    return c

def to_greenlet(argv):
    ec = get_ec()
    if len(argv) > 0:
        c = argv.pop(0)
        if isinstance(c, Greenlet):
            c.argv += argv
        else:
            c = Greenlet(ec.eventloop, [c] + argv)
    else:
        c = Greenlet(ec.eventloop, argv)
    if c.is_exhausted():
        raise space.OldError(u"attempting to put exhausted greenlet into queue")
    return c

class Greenlet(space.Object):
    def __init__(self, parent, argv):#, debug_hook):
        self.parent = parent
        self.handle = None
        self.argv = argv
        self.unwinder = None
        #self.debug_hook = debug_hook

    def getattr(self, name):
        if name == u'parent':
            return self.parent or space.null
        return space.Object.getattr(self, name)

    def repr(self):
        return u"<greenlet>"

    def is_exhausted(self):
        return self.handle is not None and self.handle.is_empty()

@Greenlet.instantiator
def greenlet(argv):
    ec = get_ec()
    return Greenlet(ec.current, argv)#, ec.debug_hook)

@Continuation.wrapped_callback
def new_greenlet(cont):
    ec = get_ec()
    self = ec.current
    argv, self.argv = self.argv, [] # XXX: Throw into empty greenlet won't happen.
    try:
        if len(argv) == 0:
            raise space.OldError(u"greenlet with no arguments")
        func = argv.pop(0)
        argv = argv_expand(func.call(argv))
        unwinder = None
    except space.Unwinder as unwinder:
        argv = []
    assert self == ec.current
    parent = self.parent
    while parent and parent.handle.is_empty():
        # note that non-initiated or non-activated parent is invalid.
        parent = parent.parent
    assert parent is not None
    parent.argv.extend(argv)
    parent.unwinder = unwinder

    ec.current = parent
    self.handle, parent.handle = parent.handle, self.handle
    return self.handle # XXX: note that the handle must not be null for this to work.

def switch(argv):
    ec = get_ec()
    target = argv.pop(0)
    self = ec.current
    #self.debug_hook = ec.debug_hook
    if not isinstance(target, Greenlet):
        raise space.OldError(u"first argument to 'switch' not a greenlet")
    if ec.current == target:
        argv, self.argv = self.argv, []
        argv.extend(argv)
        return argv_compact(argv)
    if target.handle is not None and target.handle.is_empty():
        raise space.OldError(u"empty greenlet")
    target.argv.extend(argv)
    ec.current = target
    if target.handle:
        self.handle, target.handle = target.handle, self.handle
        self.handle.switch()
    else:
        self.handle = Continuation()
        self.handle.init(new_greenlet)
    #ec.debug_hook = self.debug_hook
    argv, self.argv = self.argv, []
    if self.unwinder:
        unwinder, self.unwinder = self.unwinder, None
        raise unwinder
    return argv_compact(argv)
Greenlet.interface.methods[u'switch'] = space.Builtin(switch)

def argv_compact(argv):
    if len(argv) == 0:
        return space.null
    if len(argv) == 1:
        return argv[0]
    return space.List(argv)

def argv_expand(obj):
    if obj is space.null:
        return []
    if not isinstance(obj, space.List):
        return [obj]
    return obj.contents
