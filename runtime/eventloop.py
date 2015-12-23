import base, green, space
import time

class EventLoopState:
    sleepers = None
    queue = None
state = EventLoopState()

def init():
    state.sleepers = []
    state.queue = []

inf = float("inf")

def run():
    while len(state.queue) > 0 or len(state.sleepers) > 0:
        queue = state.queue
        state.queue = []
        print 'QUEUE', len(queue)
        for argv in queue:
            # The queue invokes on both greenlets and functions
            # This is used to ensure that triggering an event
            # will not cause greenlet switch.
            assert len(argv) > 0
            if isinstance(argv[0], green.Greenlet):
                green.switch(argv)
            else:
                green.switch([green.greenlet(argv)])
            print 'STEP', len(queue)
        print 'FLUSH', len(queue)
        #now = time.time()
        #timeout = inf
        #sleepers = state.sleepers
        state.sleepers = []
        #for wakeup, sleeper in sleepers:
        #    if wakeup <= now:
        #        state.queue.append([sleeper, space.Float(now)])
        #    else:
        #        timeout = min(timeout, wakeup)
        #        state.sleepers.append((wakeup, sleeper))
        #if len(state.queue) == 0 and len(state.sleepers) > 0:
        #    wait = timeout - now
        #    if wait > 0:
        #        time.sleep(wait)

@base.builtin
def schedule(argv):
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
    assert green.process.current != green.process.topmost, "bad context for greenlet sleep"
    assert green.process.current is not None
    trigger_time = time.time() + duration.number
    state.sleepers.append((trigger_time, green.process.current))
    print 'SLEEP'
    return green.switch([green.process.topmost])

@space.signature(space.Float, space.Object)
def sleep_2(duration, func):
    trigger_time = time.time() + duration.number
    state.sleepers.append((trigger_time, func))
    return space.null
