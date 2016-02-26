from rpython.rlib.objectmodel import we_are_translated, keepalive_until_here
#from rpython.rlib.rthread import ThreadLocalReference
#from rpython.rlib import rgc
from stdlib import api # XXX: perhaps give every module an init?
                       # Probably better way is to move the path resolution from api into here.
import vectormath
from util import STDIN, STDOUT, STDERR, read_file, write
from continuations import Continuation
from evaluator.loader import TraceEntry
import base
import space
import time
import module_resolution
import os
import pathobj

class ExecutionContext(object):
    def __init__(self, config, lever_path):
        self.config = config
        self.lever_path = lever_path
        self.sthread = None                 # Stacklets
        self.queue = []                     # Event queue.
        self.sleepers = []                  # Holds the sleeping greenlets.
        self.current = Greenlet(None, [])
        self.eventloop = self.current

class GlobalState(object):
    ec = None

def get_ec():
    return g.ec

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
        
        g.ec = ec = ExecutionContext(config, lever_path)
        api.init(lever_path)
        vectormath.init_random()

        argv = [normal_startup]
        for arg in raw_argv[1:]:
            argv.append(space.String(arg.decode('utf-8')))
        schedule(argv)

        try:
            # This behavior is similar to javascript's event loop, except that
            # the messages put into queue are handled by greenlets rather than
            # callbacks. The greenlets allow synchronous notation for
            # asynchronous programs.
            while len(ec.queue) + len(ec.sleepers) > 0:
                queue, ec.queue = ec.queue, []
                for item in queue:
                    switch([item])
                now = time.time()
                timeout = inf
                sleepers, ec.sleepers = ec.sleepers, []
                for sleeper in sleepers:
                    if sleeper.wakeup <= now:
                        sleeper.greenlet.argv.append(space.Float(now))
                        ec.queue.append(sleeper.greenlet)
                    else:
                        timeout = min(timeout, sleeper.wakeup)
                        ec.sleepers.append(sleeper)
                if len(ec.queue) == 0 and len(ec.sleepers) > 0 and now < timeout:
                    time.sleep(timeout - now)
        except space.Unwinder as unwinder:
            exception = unwinder.exception
            if isinstance(exception, space.LSystemExit):
                return int(exception.status)
            print_traceback(unwinder)
            return 1
        return 0
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
    ec.queue.append(c)
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
def sleep_greenlet(duration):
    ec = get_ec()
    if ec.current == ec.eventloop:
        raise space.OldError(u"bad context for greenlet sleep")
    assert ec.current.is_exhausted() == False
    wakeup = time.time() + duration.number
    ec.sleepers.append(Suspended(wakeup, ec.current))
    return switch([ec.eventloop])

@space.signature(space.Float, space.Object)
def sleep_callback(duration, func):
    ec = get_ec()
    wakeup = time.time() + duration.number
    ec.sleepers.append(Suspended(wakeup, to_greenlet([func])))
    return space.null

def to_greenlet(argv):
    ec = get_ec()
    if len(argv) > 0 and isinstance(argv[0], Greenlet):
        c = argv.pop(0)
        assert isinstance(c, Greenlet)
        c.argv += argv
    else:
        c = Greenlet(ec.eventloop, argv)
    if c.is_exhausted():
        raise space.OldError(u"attempting to put exhausted greenlet into queue")
    return c

class Greenlet(space.Object):
    def __init__(self, parent, argv):
        self.parent = parent
        self.handle = None
        self.argv = argv
        self.unwinder = None

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
    return Greenlet(get_ec().current, argv)

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

def print_traceback(unwinder):
    out = u""
    if len(unwinder.traceback) > 0:
        out = u"\033[31mTraceback:\033[36m\n"
    for entry in reversed(unwinder.traceback.contents):
        if not isinstance(entry, TraceEntry):
            continue
        pc = entry.pc
        constants = entry.constants
        sourcemap = entry.sourcemap
        name, col0, lno0, col1, lno1 = pc_location(pc, constants, sourcemap)
        out += u"    %s: %d,%d : %d,%d\n" % (name.repr(), lno0, col0, lno1, col1)
    out += u"\033[31m"
    out += space.get_interface(unwinder.exception).name
    out += u":\033[0m"
    write(STDERR, out + u" " + unwinder.exception.repr() + u"\n")

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
    raise space.OldError(u"invalid sourcemap format")
