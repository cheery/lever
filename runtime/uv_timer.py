from uv_handle import Handle2, check, Handle2_close
from async_io import *
import rlibuv as uv
import uv_util
import core
import async_io

# Remember that any handle must be closed after use.
class Timer(Handle2):
    def __init__(self, timer):
        Handle2.__init__(self, rffi.cast(uv.handle_ptr, timer))
        self.timer = timer
        self.on_tick = Event()
        self.events += [self.on_tick]

    def getattr(self, name):
        if name == u"on_tick":
            return self.on_tick
        return Handle2.getattr(self, name)

@Timer.instantiator2(signature())
def Timer_init():
    ec = core.get_ec()
    timer = ec.handles.create(uv.timer_ptr, uv.timer_init)
    return Timer(timer)

@Timer.method(u"start", signature(Timer, Float, Float, optional=1))
def Timer_start(self, delay, repeat):
    if repeat is None:
        rep = 0
    else:
        rep = int(repeat.number * 1000)
    check( uv.timer_start(self.timer, _on_tick_, int(delay.number*1000), 0) )
    return null

def _on_tick_(timer):
    ec = core.get_ec()
    self = ec.handles.get(timer, Timer)
    try:
        Event_dispatch(self.on_tick, [])
    except Unwinder as unwinder:
        core.root_unwind(unwinder)

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

# It looks like this was a brain fart for a long while now.
# # Close is required anyway, because the Timer may have events waiting on it.
# # TODO: on Timer.close, close the .on_tick event handle as well.
# @Timer.method(u"close", signature(Timer))
# def Timer_close(self):
#     Handle2_close(self)
#     Event_close(self.on_tick) # TODO: this might actually be
#                               #       a recurring pattern here.
#     return null
