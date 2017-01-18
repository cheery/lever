from space import *
import core

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

@Queue.instantiator2(signature())
def _():
    return Queue()
#        self.closed = False

#@Queue.method(u"close", signature(Queue))
#def Queue_close(self):
#    self.closed = True
#    return null # TODO: implement close properly.
        
@Queue.method(u"append", signature(Queue, Object))
def Queue_append(self, obj):
    if self.greenlet is not None:
        ec = core.get_ec()
        self.greenlet.argv.append(obj)
        ec.enqueue(self.greenlet)
        self.greenlet = None
    else:
        self.items.append(obj)
    return null

@Queue.method(u"wait", signature(Queue))
def Queue_wait(self):
    if len(self.items) > 0:
        return self.items.pop(0)
    else:
        ec = core.get_ec()
        self.greenlet = ec.current
        return core.switch([ec.eventloop])
