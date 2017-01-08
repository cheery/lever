from rpython.rlib.rstacklet import StackletThread
from rpython.rlib.objectmodel import specialize
import core

class SThread(StackletThread):
    def __init__(self, config):
        StackletThread.__init__(self, config)
        self.cont = None

def get_sthread():
    ec = core.get_ec()
    if not ec.sthread:
        ec.sthread = SThread(ec.config)
    return ec.sthread

# Continuation represents either live or empty continuation.
# It is never 'blank', assuming you call 'init' immediately after positioning the continuation.
class Continuation(object):
    def __init__(self):
        self.sthread = sthread = get_sthread()
        self.h = sthread.get_null_handle()
        self.gate = False

    def is_empty(self):
        return self.sthread.is_empty_handle(self.h) or not self.gate

    def init(self, callback):
        sthread = self.sthread
        assert sthread.cont is None
        sthread.cont = self
        self.h = sthread.new(callback)

    def switch(self):
        sthread = get_sthread()
        assert not self.is_empty(), "not so fatal error: empty switch continuation"
        self.h = sthread.switch(self.h)

    @staticmethod
    def wrapped_callback(callback):
        def _wrapped_callback(head, arg):
            sthread = get_sthread()
            this, sthread.cont = sthread.cont, None
            this.h = head
            this.gate = True
            cont = callback(this)
            assert not cont.is_empty(), "fatal error: empty return continuation"
            cont.gate = False
            return cont.h
        _wrapped_callback.__name__ = callback.__name__
        return _wrapped_callback
