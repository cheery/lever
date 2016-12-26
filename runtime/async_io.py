# Maintains an threadpool to provide async behavior for I/O,
# in platform-independent manner.
# The same method is used by other async libraries because
# async-support in operating systems was not very great or portable.
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib import rthread, rpoll
from rpython.rlib.rarithmetic import r_longlong, ovfcheck_float_to_longlong
from rpython.rlib.rthread import start_new_thread, allocate_lock, RThreadError
from rpython.rlib.rfile import create_stdio
from space import *
import time
import main
import os, sys
import eventual

# TODO: error handling?
def create_eventloop_handle(io, ec):
    sz = eventual.et_sizeof(eventual.MAIN_LOOP)
    loop_handle = lltype.malloc(rffi.CCHARP.TO, sz, flavor='raw')
    eventual.et_init(loop_handle)
    return loop_handle

def process_events(io, ec, now, until):
    if len(ec.queue) > 0:
        timeout = 0
    elif len(ec.sleepers) > 0:
        timeout = int((until - now)*1000)
    elif io.task_count > 0:
        timeout = eventual.INFINITE
    else:           # If there are no tasks that
        timeout = 0 # need waiting, we should just
                    # reset stuff and then proceed.
    eventual.et_wait(ec.handle, timeout)

class AsyncIO(object):
    def __init__(self):
        # Should go into execution context.
        self.task_count = 0         # Reveals whether there is work pending.
        self.fddict = {}
        #self.fdstate = {}

        (self.stdin,
         self.stdout,
         self.stderr) = create_stdio()

        # Workers subsystem
        self.worker_quota = 6
        self.task_queue = []
        self.task_lock = allocate_lock()
        self.task_wait_lock = allocate_lock() # The rpython locks are internally
        self.task_wait_count = 0              # conditions, so this should work.

    def new_task(self, func, argv):
        ec = main.get_ec()
        greenlet = ec.current
        self.task_count += 1
        # This side is not aware about task timeouts.
        with self.task_lock:
            self.task_queue.append((ec, greenlet, func, argv))
            if self.task_wait_count > 0:
                self.task_wait_lock.release()
            elif self.worker_quota > 0:
                self.worker_quota -= 1
                start_new_thread(async_io_thread, ())
        return main.switch([ec.eventloop])

#class FDState(object):
#    def __init__(self, greenlet):
#        self.greenlet = greenlet

## new starting thread starts and ends without arguments.
def async_io_thread():
    rthread.gc_thread_start()
    async_io_loop(main.g.io)
    rthread.gc_thread_die()

def async_io_loop(io):
    while True:
        # Checking whether there's task 
        ec, greenlet, func, argv = None, None, None, []
        with io.task_lock:
            if len(io.task_queue) > 0:
                ec, greenlet, func, argv = io.task_queue.pop(0)
            else:
                io.task_wait_lock.acquire(False)
                io.task_wait_count += 1
        if func is None:
            res = acquire_timed(io.task_wait_lock, 10000000) # timeout 10 seconds
            # Either timeout or release happened.
            with io.task_lock:
                io.task_wait_count -= 1 # we are not waiting for now.
                if res == RPY_LOCK_FAILURE and len(io.task_queue) == 0:
                    io.worker_quota += 1
                    return # At this point it is very clear that
                           # this task is no longer needed.
        else:
            try:
                res = func(argv)
                greenlet.argv.append(res)
            except Unwinder as unwinder:
                greenlet.unwinder = unwinder
            except Exception as exc:
                greenlet.unwinder = unwind(LError(
                    u"Undefined error at async_io_thread(): " +
                        str(exc).decode('utf-8') + u"\n"))
            # I hope these are atomic operations.
            ec.queue.append(greenlet)
            io.task_count -= 1
            eventual.et_notify(ec.handle)

# Taken from pypy
def acquire_timed(lock, microseconds):
    """Helper to acquire an interruptible lock with a timeout."""
    endtime = (time.time() * 1e6) + microseconds
    while True:
        result = lock.acquire_timed(microseconds)
        if result == RPY_LOCK_INTR:
            # Run signal handlers if we were interrupted
            # TODO: lever signal handlers?
            #space.getexecutioncontext().checksignals()
            if microseconds >= 0:
                microseconds = r_longlong((endtime - (time.time() * 1e6))
                                          + 0.999)
                # Check for negative values, since those mean block
                # forever
                if microseconds <= 0:
                    result = RPY_LOCK_FAILURE
        if result != RPY_LOCK_INTR:
            break
    return result

RPY_LOCK_FAILURE, RPY_LOCK_ACQUIRED, RPY_LOCK_INTR = range(3)
