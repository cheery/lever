from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from space import *
import core
import uv_callback
from uv_handle import Handle, check, Handle_close
import rlibuv as uv

class Event(Object):
    def __init__(self):
        self.callbacks = []
        self.waiters = []

    #TODO: on delete/discard, drop
    #      waiters to queue with
    #      error handlers.

@Event.instantiator2(signature())
def _():
    return Event()

@Event.method(u"close", signature(Event))
def Event_close(self):
    self.callbacks = []
    self.waiters = []
    # TODO: don't just drop the waiters.
    return null

@Event.method(u"dispatch", signature(Event, variadic=True))
def Event_dispatch(self, argv):
    ec = core.get_ec()

    for cb in self.callbacks:
        ec.enqueue(core.to_greenlet([cb] + argv))
    waiters, self.waiters = self.waiters, []
    for waiter in waiters:
        waiter.argv.extend(argv)
        ec.enqueue(waiter)
    return null

@Event.method(u"register", signature(Event, Object))
def Event_register(self, cb):
    self.callbacks.append(cb)
    return null

@Event.method(u"unregister", signature(Event, Object))
def Event_unregister(self, cb):
    try:
        self.callbacks.remove(cb) # Just crashing on problem for now.
        return null
    except ValueError as _:
        raise unwind(LError(u"callback not registered"))
    
@Event.method(u"wait", signature(Event)) # TODO: with timeout perhaps?
def Event_wait(self):
    ec = core.get_ec()
    self.waiters.append(ec.current)
    return core.switch([ec.eventloop])


class Queue(Object):
    def __init__(self):
        self.items = []
        self.greenlet = None
        self.closed = False

    def getattr(self, name):
        if name == u"length":
            return Integer(len(self.items))
        return Object.getattr(self, name)

    def append(self, obj):
        if self.closed: # TODO: add granular exception.
            raise unwind(LError(u"queue is closed"))
        if self.greenlet is not None:
            ec = core.get_ec()
            self.greenlet.argv.append(obj)
            ec.enqueue(self.greenlet)
            self.greenlet = None
        else:
            self.items.append(obj)

@Queue.instantiator2(signature())
def _():
    return Queue()

@Queue.method(u"close", signature(Queue))
def Queue_close(self):
    self.closed = True
    return null # TODO: implement close properly.
        
@Queue.method(u"append", signature(Queue, Object))
def Queue_append(self, obj):
    self.append(obj)
    return null

@Queue.method(u"wait", signature(Queue))
def Queue_wait(self):
    if len(self.items) > 0:
        return self.items.pop(0)
    elif self.closed: # TODO: add granular exception.
        raise unwind(LError(u"queue is closed"))
    else:
        ec = core.get_ec()
        self.greenlet = ec.current
        return core.switch([ec.eventloop])

class Timer(Handle):
    def __init__(self, timer):
        Handle.__init__(self, rffi.cast(uv.handle_ptr, timer))
        self.timer = timer
        self.on_tick = Event()

    def getattr(self, name):
        if name == u"on_tick":
            return self.on_tick
        return Handle.getattr(self, name)

@Timer.instantiator2(signature()) # Remember that timers must be closed.
def Timer_init():
    ec = core.get_ec()
    timer = lltype.malloc(uv.timer_ptr.TO, flavor="raw", zero=True)
    uv.timer_init(ec.uv_loop, timer)
    self = Timer(timer)
    uv_callback.push(ec.uv__timer, self)
    return self

@Timer.method(u"start", signature(Timer, Float, Float, optional=1))
def Timer_start(self, delay, repeat):
    if repeat is None:
        rep = 0
    else:
        rep = int(repeat.number * 1000)
    check( uv.timer_start(self.timer, _timer_callback_, int(delay.number*1000), 0) )
    return null

def _timer_callback_(handle):
    ec = core.get_ec()
    self = uv_callback.peek(ec.uv__timer, handle)
    Event_dispatch(self.on_tick, [])

@Timer.method(u"set_repeat", signature(Timer, Float))
def Timer_set_repeat(self, value):
    uv.timer_set_repeat(self.timer, int(value.number*1000))
    return null

@Timer.method(u"again", signature(Timer))
def Timer_again(self):
    check( uv.timer_again(self.timer) )
    return null

@Timer.method(u"stop", signature(Timer))
def Timer_stop(self):
    check( uv.timer_stop(self.timer) )
    return null

# Close is required anyway, because the Timer may have events waiting on it.
@Timer.method(u"close", signature(Timer))
def Timer_close(self):
    timer = self.timer
    Handle_close(self)
    # TODO: on Timer.close, close the .on_tick event handle as well.
    ec = core.get_ec()
    uv_callback.drop(ec.uv__timer, timer)
    return null
