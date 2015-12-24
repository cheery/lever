import base, green, space
import time

class EventLoop(object):
    def __init__(self):
        self.sleepers = []
        self.queue = []

def init():
    green.process.eventloop = EventLoop()

inf = float("inf")

def run():
    state = green.process.eventloop
    while len(state.queue) > 0 or len(state.sleepers) > 0:
        queue = state.queue
        state.queue = []
        for argv in queue:
            # The queue invokes on both greenlets and functions
            # This is used to ensure that triggering an event
            # will not cause greenlet switch.
            assert len(argv) > 0
            if isinstance(argv[0], green.Greenlet):
                green.switch(argv)
            else:
                green.switch([green.greenlet(argv)])
        now = time.time()
        timeout = inf
        sleepers = state.sleepers
        state.sleepers = []
        for wakeup, sleeper in sleepers:
            if wakeup <= now:
                state.queue.append([sleeper, space.Float(now)])
            else:
                timeout = min(timeout, wakeup)
                state.sleepers.append((wakeup, sleeper))
        if len(state.queue) == 0 and len(state.sleepers) > 0:
            wait = timeout - now
            if wait > 0:
                time.sleep(wait)

@base.builtin
def schedule(argv):
    state = green.process.eventloop
    state.queue.append(argv)
    return space.null

@base.builtin
def sleep(argv):
    if len(argv) == 1:
        return sleep_1(argv)
    elif len(argv) == 2:
        return sleep_2(argv)
    else:
        raise space.Error(u"expected 1 or 2 arguments to sleep(), got %d" % len(argv))

@space.signature(space.Float)
def sleep_1(duration):
    state = green.process.eventloop
    assert green.process.current != green.process.topmost, "bad context for greenlet sleep"
    assert green.process.current is not None
    trigger_time = time.time() + duration.number
    state.sleepers.append((trigger_time, green.process.current))
    return green.switch([green.process.topmost])

@space.signature(space.Float, space.Object)
def sleep_2(duration, func):
    state = green.process.eventloop
    trigger_time = time.time() + duration.number
    state.sleepers.append((trigger_time, func))
    return space.null
