from rpython.rlib.objectmodel import we_are_translated, keepalive_until_here
from rpython.rlib import jit
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
#from rpython.rlib.rthread import ThreadLocalReference
#from rpython.rlib import rgc
from stdlib import api # XXX: perhaps give every module an init?
                       # Probably better way is to move the path resolution from api into here.
import vectormath
from util import STDIN, STDOUT, STDERR, read_file, write
from continuations import Continuation
from evaluator.loader import TraceEntry
import async_io
import base
import space
import time
import module_resolution
import os
import pathobj
import rlibuv as uv

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
        #self.debug_hook = None

    def enqueue(self, task):
        if len(self.queue) == 0 and not uv.is_active(rffi.cast(uv.handle_ptr, self.uv_idler)):
            uv.idle_start(self.uv_idler, run_queued_tasks)
        self.queue.append(task)

class GlobalState(object):
    ec = None
    io = None

def get_ec():
    return g.ec

def run_queued_tasks(handle):
    ec = get_ec()
    queue, ec.queue = ec.queue, []
    for item in queue:
        root_switch(ec, [item])
    if len(ec.queue) == 0: # trick.
        uv.idle_stop(ec.uv_idler)

@jit.dont_look_inside # cast_ptr_to_adr
def wakeup_sleeper(handle):
    ec = get_ec()

    task = ec.uv_sleepers.pop( rffi.cast_ptr_to_adr(handle) )
    ec.enqueue(task)

    uv.timer_stop(handle)
    uv.close(rffi.cast(uv.handle_ptr, handle), uv.free)

#global_state = ThreadLocalReference(GlobalState)
g = GlobalState()

inf = float("inf")

def new_entry_point(config, default_lever_path=u''):
    def entry_point(raw_argv):
        lever_path = os.environ.get('LEVER_PATH')
        if lever_path is None:
            lever_path = pathobj.parse(default_lever_path)
        else:
            lever_path = pathobj.os_parse(lever_path.decode('utf-8'))
        lever_path = pathobj.concat(pathobj.getcwd(), lever_path)
        
        # This should happen only once.
        #g.io = MiniIO()

        uv_loop = uv.default_loop()
        uv_idler = uv.malloc_bytes(uv.idle_ptr, uv.handle_size(uv.IDLE))
        uv.idle_init(uv_loop, uv_idler)

        uv_stdin  = async_io.initialize_tty(uv_loop, 0, 1)
        uv_stdout = async_io.initialize_tty(uv_loop, 1, 0)
        uv_stderr = async_io.initialize_tty(uv_loop, 2, 0)
        #TODO: consider whether these should plug to base.
        base.module.setattr_force(u"stdin",  uv_stdin)
        base.module.setattr_force(u"stdout", uv_stdout)
        base.module.setattr_force(u"stderr", uv_stderr)

        g.ec = ec = ExecutionContext(config, lever_path, uv_loop, uv_idler)
        api.init(lever_path)
        vectormath.init_random()

        argv = [normal_startup]
        for arg in raw_argv[1:]:
            argv.append(space.String(arg.decode('utf-8')))
        schedule(argv)

        uv.run(ec.uv_loop, uv.RUN_DEFAULT)

        #uv.loop_close(ec.uv_loop)

        uv.tty_reset_mode()
        return ec.exit_status
    return entry_point

@space.Builtin
def normal_startup(argv):
    if len(argv) > 0:
        main_script = argv[0]
    else:
        main_script = pathobj.concat(get_ec().lever_path, pathobj.parse(u"app/main.lc"))
        main_script = space.String(pathobj.os_stringify(main_script))
    module = module_resolution.start(main_script)
    try:
        main_func = module.getattr(u"main")
    except space.Unwinder as unwinder:
        pass # in this case main_func just isn't in the module.
    else:
        main_func.call([space.List(argv)])
    return space.null

@base.builtin
def schedule(argv):
    ec = get_ec()
    c = to_greenlet(argv)
    ec.enqueue(c)
    return c

class Suspended(object):
    _immutable_fields_ = ['wakeup', 'greenlet']
    def __init__(self, wakeup, greenlet):
        assert isinstance(greenlet, Greenlet)
        self.wakeup = wakeup
        self.greenlet = greenlet

@base.builtin
def sleep(argv):
    if len(argv) == 1:
        return sleep_greenlet(argv)
    elif len(argv) == 2:
        return sleep_callback(argv)
    else:
        raise space.OldError(u"expected 1 or 2 arguments to sleep(), got %d" % len(argv))

@space.signature(space.Float)
@jit.dont_look_inside # cast_ptr_to_adr
def sleep_greenlet(duration):
    ec = get_ec()
    if ec.current == ec.eventloop:
        raise space.OldError(u"bad context for greenlet sleep")
    assert ec.current.is_exhausted() == False

    uv_sleeper = uv.malloc_bytes(uv.timer_ptr, uv.handle_size(uv.TIMER))
    ec.uv_sleepers[rffi.cast_ptr_to_adr(uv_sleeper)] = ec.current
    uv.timer_init(ec.uv_loop, uv_sleeper)
    uv.timer_start(uv_sleeper, wakeup_sleeper, int(duration.number*1000), 0)

    return switch([ec.eventloop])

@space.signature(space.Float, space.Object)
@jit.dont_look_inside # cast_ptr_to_adr
def sleep_callback(duration, func):
    ec = get_ec()

    uv_sleeper = uv.malloc_bytes(uv.timer_ptr, uv.handle_size(uv.TIMER))
    ec.uv_sleepers[rffi.cast_ptr_to_adr(uv_sleeper)] = to_greenlet([func])
    uv.timer_init(ec.uv_loop, uv_sleeper)
    uv.timer_start(uv_sleeper, wakeup_sleeper, int(duration.number*1000), 0)
    return space.null

def to_greenlet(argv):
    ec = get_ec()
    if len(argv) > 0 and isinstance(argv[0], Greenlet):
        c = argv.pop(0)
        assert isinstance(c, Greenlet)
        c.argv += argv
    else:
        c = Greenlet(ec.eventloop, argv)#, ec.debug_hook)
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

@base.builtin
def getcurrent(argv):
    return get_ec().current

@base.builtin # XXX: replace with instantiator
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

def root_switch(ec, argv):
    try:
        switch(argv)
    except space.Unwinder as unwinder:
        exception = unwinder.exception
        #if isinstance(exception, space.LSystemExit):
        #    return int(exception.status)
        base.print_traceback(unwinder.exception)

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

@base.builtin
@space.signature(space.Integer, optional=1)
def exit(obj):
    ec = get_ec()
    ec.exit_status = 0 if obj is None else int(obj.value)
    uv.stop(ec.uv_loop)
    ec.enqueue(ec.current)        # Trick to ensure we get Discard -exception here
    return switch([ec.eventloop]) # Once they are created.
