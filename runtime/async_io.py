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

def process_events(io, ec, now, until):
    if len(ec.queue) > 0:
        timeout = 0
    elif len(ec.sleepers) > 0:
        timeout = int((until - now)*1000)
    else:
        timeout = INFINITE

    if io.task_count == 0:
        if timeout > 0:
            time.sleep(timeout)
    else:
        system_event_loop(io, ec, timeout)


#defaultevents = rpoll.POLLIN | rpoll.POLLOUT | rpoll.POLLPRI

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

_WIN32 = sys.platform == "win32"
_LINUX = sys.platform.startswith('linux')

if _WIN32:
    from rpython.rlib.rwin32 import *
    OVERLAPPED = Struct('OVERLAPPED', [
        ('Internal', ULONG_PTR),
        ('InternalHigh', ULONG_PTR),
        ('Offset', DWORD),
        ('OffsetHigh', DWORD),
        ('hEvent', HANDLE),
    ])
    LPOVERLAPPED = lltype.Ptr(OVERLAPPED)

    CreateIoCompletionPort = winexternal('CreateIoCompletionPort',
        [HANDLE, HANDLE, ULONG_PTR, DWORD], HANDLE)
    GetQueuedCompletionStatus = winexternal('GetQueuedCompletionStatus',
        [HANDLE, LPDWORD, lltype.Ptr(ULONG_PTR), LPOVERLAPPED, DWORD], BOOL)
    PostQueuedCompletionStatus = winexternal('PostQueuedCompletionStatus',
        [HANDLE, DWORD, ULONG_PTR, LPOVERLAPPED], BOOL)

    def system_event_loop(io, ec, timeout):
        transferred = lltype.malloc(LPDWORD, flavor='raw')
        completionKey = lltype.malloc(ULONG_PTR, flavor='raw')
        ovl = lltype.malloc(LPOVERLAPPED, flavor='raw')

        try:
            res = GetQueuedCompletionStatus(ec.iocp,
                transferred, completionkey, ovl, timeout)
            handle = ovl[0]
            if res > 0 and handle != rffi.NULL:
                if ec.handle == handle:
                    pass # eventloop was notified and can continue.
        finally:
            lltype.free(transferred, flavor='raw')
            lltype.free(completionKey, flavor='raw')
            lltype.free(ovl, flavor='raw')

    def create_eventloop_handle(io, ec):
        ec.iocp = CreateIoCompletionPort(
            INVALID_HANDLE_VALUE, rffi.NULL, 0, 0)
        handle = lltype.malloc(OVERLAPPED, flavor='raw')
        rffi.c_memset(handle, 0, rffi.sizeof(OVERLAPPED))
        return handle

    def notify_eventloop(ec):
        PostQueuedCompletionStatus(ec.iocp, 0, rffi.NULL, ec.handle)
elif _LINUX:
    INFINITE = -1

    eci = ExternalCompilationInfo(
        includes = ['sys/eventfd.h']
    )
    eventfd = rffi.llexternal("eventfd", [rffi.INT, rffi.INT], rffi.INT,
        compilation_info=eci)

    def system_event_loop(io, ec, timeout):
        try:
            result = rpoll.poll(io.fddict, timeout)
        except rpoll.PollError as error:
            print "Poll error: " + error.get_msg()
            # TODO: consider what to do for these errors...
        else:
            # TODO: allow read/write on same fd.
            for fd, revents in result:
                if fd == ec.handle:
                    # The async processor did all the work, we just need to
                    # reset the handle for further notifications.
                    os.read(ec.handle, 8)
                else:
                    pass
                    #greenlet = io.fdstate[fd]
                    #del io.fdstate[fd]
                    #ec.queue.append(greenlet)
                    #io.task_count -= 1 # A task was completed.
                                       # One must also increment the task counter
                                       # when introducing a new task.

    def create_eventloop_handle(io, ec):
        fd = eventfd(0, 0)
        io.fddict[fd] = rpoll.POLLIN
        return fd

    def notify_eventloop(ec):
        os.write(ec.handle, '\x01\x00\x00\x00\x00\x00\x00\x00')
else:
    assert False, "Only linux&win32 support for now."


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
            notify_eventloop(ec)

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
