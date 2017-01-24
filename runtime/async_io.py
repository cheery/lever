from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from space import *
import core

class Event(Object):
    def __init__(self):
        self.closed = False
        self.callbacks = []
        self.waiters = []

    def check_closed(self):
        if self.closed:
            raise unwind(LError(u"Event is closed"))
    #TODO: on delete/discard, drop
    #      waiters to queue with
    #      error handlers.

@Event.instantiator2(signature())
def _():
    return Event()

@Event.method(u"close", signature(Event))
def Event_close(self):
    self.closed = True
    # TODO: don't just drop the waiters.
    #       
    self.callbacks = []
    self.waiters = []
    return null

@Event.method(u"dispatch", signature(Event, variadic=True))
def Event_dispatch(self, argv):
    ec = core.get_ec()

    for cb in self.callbacks:
        c = core.to_greenlet([cb] + argv)
        c.ec.enqueue(c)
    waiters, self.waiters = self.waiters, []
    for waiter in waiters:
        waiter.argv.extend(argv)
        waiter.ec.enqueue(waiter)
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
            self.greenlet.argv.append(obj)
            self.greenlet.ec.enqueue(self.greenlet)
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
