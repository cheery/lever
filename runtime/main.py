from rpython.rlib.objectmodel import we_are_translated, keepalive_until_here
from rpython.config.translationoption import get_combined_translation_config
from rpython.rlib.rstacklet import StackletThread
from rpython.rlib.rthread import ThreadLocalReference
from rpython.rlib import rgc
from stdlib import api # XXX: perhaps give every module an init?
from util import STDIN, STDOUT, STDERR, read_file, write
import base
import space
import time
import module_resolution

config = get_combined_translation_config(translating=True)
config.translation.continuation = True

class GlobalState(object):
    sthread = None
    eventloop = None
    ev_queue = None
    ev_sleepers = None
    origin = None
    target = None
    error = None

#global_state = ThreadLocalReference(GlobalState)
g = GlobalState()

inf = float("inf")

def entry_point(raw_argv):
    sthread = StackletThread(config)
    #g = GlobalState()
    g.target = Greenlet(sthread, None, sthread.get_null_handle(), [])
    g.target.initialized = True
    g.eventloop = g.target
    #global_state.set(g)
    api.init(raw_argv)

    g.ev_queue = []
    g.ev_sleepers = []
    argv = [normal_startup]
    for arg in raw_argv[1:]:
        argv.append(space.String(arg.decode('utf-8')))
    schedule(argv)

    rno = 0
    try:
        while len(g.ev_queue) + len(g.ev_sleepers) > 0:
            rgc.collect()
            queue, g.ev_queue = g.ev_queue, []
            for item in queue:
                # the queue did invoke on both greenlets and functions
                # then I realized the greenlet is created anyway,
                # so here we have a queue with only greenlets.
                switch([item])
            now = time.time()
            timeout = inf
            sleepers, g.ev_sleepers = g.ev_sleepers, []
            for sleeper in sleepers:
                if sleeper.wakeup <= now:
                    sleeper.greenlet.argv.append(space.Float(now))
                    g.ev_queue.append(sleeper.greenlet)
                else:
                    timeout = min(timeout, sleeper.wakeup)
                    g.ev_sleepers.append(sleeper)
            if len(g.ev_queue) == 0 and len(g.ev_sleepers) > 0 and now < timeout:
                time.sleep(timeout - now)
    except space.Error as error:
        print_traceback(error)
        rno = 1
    g.sthread = sthread
    return rno

@space.Builtin
def normal_startup(argv):
    module_src = argv[0]
    assert isinstance(module_src, space.String)
    module = space.Module(u'main', {}, extends=base.module)
    result = module_resolution.load_module(module_src.string.encode('utf-8'), module)
    try:
        main_func = module.getattr(u"main")
    except space.Error as error:
        pass # in this case main_func just isn't in the module.
    else:
        result = main_func.call([space.List(argv)])
    return space.null

@base.builtin
def schedule(argv):
    #g = global_state.get()
    if len(argv) > 0 and isinstance(argv[0], Greenlet):
        c = argv.pop(0)
        assert isinstance(c, Greenlet)
        c.argv += argv
    else:
        sthread = g.target.sthread
        c = Greenlet(sthread, g.eventloop, sthread.get_null_handle(), argv)
    if c.exhausted:
        raise space.Error(u"attempting to put exhausted greenlet into queue")
    if c == g.eventloop:
        raise space.Error(u"attempting to schedule the event loop into queue")
    g.ev_queue.append(c)
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
        raise space.Error(u"expected 1 or 2 arguments to sleep(), got %d" % len(argv))

@space.signature(space.Float)
def sleep_greenlet(duration):
    #g = global_state.get()
    if g.target == g.eventloop:
        raise space.Error(u"bad context for greenlet sleep")
    assert g.target.exhausted == False
    wakeup = time.time() + duration.number
    g.ev_sleepers.append(Suspended(wakeup, g.target))
    return switch([g.eventloop])

@space.signature(space.Float, space.Object)
def sleep_callback(duration, func):
    #g = global_state.get()
    wakeup = time.time() + duration.number
    g.ev_sleepers.append(Suspended(wakeup, schedule([func])))
    return space.null

class Greenlet(space.Object):
    def __init__(self, sthread, parent, handle, argv):
        self.sthread = sthread
        self.parent = parent
        self.handle = handle
        self.argv = argv
        self.exhausted = False
        self.initialized = False

    def getattr(self, name):
        if name == u'parent':
            return self.parent or space.null
        return space.Object.getattr(self, name)

    def repr(self):
        return u"<greenlet>"

@base.builtin
def getcurrent(argv):
    #g = global_state.get()
    return g.target

@base.builtin # XXX: replace with instantiator
def greenlet(argv):
    #g = global_state.get()
    sthread = g.target.sthread
    return Greenlet(sthread, g.target, sthread.get_null_handle(), argv)

def new_greenlet(head, _):
    #print "init"
    #g = global_state.get()
    this = g.target
    try:
        rgc.collect()
        argv = end_transfer(g, head)
        if len(argv) == 0:
            raise space.Error(u"greenlet with no arguments")
        func = argv.pop(0)
        argv = argv_expand(func.call(argv))
    except space.Error as error:
        g.error = error
        argv = []
    assert this == g.target
    assert not this.exhausted
    g.target.exhausted = True
    parent = g.target.parent
    assert parent is not None
    while parent.exhausted:
        parent = parent.parent
    #print "quit"
    return begin_transfer(g, parent, argv) # XXX: note that reparented handle 
                                           #      must not be null for this to work.

def switch(argv):
    #print "switch"
    #g = global_state.get()
    target = argv.pop(0)
    if not isinstance(target, Greenlet):
        raise space.Error(u"first argument to 'switch' not a greenlet")
    if target.exhausted:
        raise space.Error(u"dead greenlet")
    if g.target == target:
        return argv_compact(argv)
    handle = begin_transfer(g, target, argv)
    if not g.target.initialized:
        g.target.initialized = True
        h = g.target.sthread.new(new_greenlet)
    else:
        h = g.target.sthread.switch(handle)
    return argv_compact(end_transfer(g, h))

Greenlet.interface.methods[u'switch'] = space.Builtin(switch)

def begin_transfer(g, target, argv):
    #print "begin_transfer"
    g.origin = g.target
    g.target = target
    target.argv += argv
    return target.handle

def end_transfer(g, head):
    #print "end_transfer"
    g.origin.handle = head
    g.target.handle = g.target.sthread.get_null_handle()
    argv, g.target.argv = g.target.argv, []
    if g.error is not None:
        error, g.error = g.error, None
        raise error
    return argv

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
