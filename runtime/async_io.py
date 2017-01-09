from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rlib.rstring import StringBuilder, UnicodeBuilder
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from space import *
import base
import core
import rlibuv as uv

class Handle(Object):
    def __init__(self, handle):
        self.handle = handle
        self.closed = False
        self.buffers = []

    def getattr(self, name):
        if name == u"active":
            return boolean(uv.is_active(self.handle))
        if name == u"closing":
            return boolean(uv.is_closing(self.handle))
        if name == u"closed":
            return boolean(self.closed)
#        if name == u"ref":
#            return boolean(uv.has_ref(self.handle))
        return Object.getattr(self, name)

    # All handles are resources, so I don't think doing
    # automatic close on losing them would do any good.

@Handle.method(u"close", signature(Handle))
def Handle_close(self):
    ec = core.get_ec()
    slot = async_begin(self.handle, ec.uv_closing, self)
    uv.close(self.handle, Handle_close_cb)
    return async_end(ec, slot, self.handle, ec.uv_closing, 0)

@jit.dont_look_inside # cast_ptr_to_adr
def Handle_close_cb(handle):
    ec = core.get_ec()
    slot, self = ec.uv_closing.pop(rffi.cast_ptr_to_adr(handle))
    self.closed = True
    # Should be safe to release them here.
    buffers, self.buffers = self.buffers, []
    for pointer in buffers:
        lltype.free(pointer, flavor='raw')
    lltype.free(handle, flavor='raw')
    self.handle = lltype.nullptr(uv.handle_ptr.TO)
    slot.response(ec, space.null)

@Handle.method(u"get_send_buffer_size", signature(Handle))
def Handle_get_send_buffer_size(self):
    value = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.send_buffer_size(self.handle, value) )
        return Integer(rffi.r_long(value[0]))
    finally:
        lltype.free(value, flavor='raw')

@Handle.method(u"get_recv_buffer_size", signature(Handle))
def Handle_get_recv_buffer_size(self):
    value = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.recv_buffer_size(self.handle, value) )
        return Integer(rffi.r_long(value[0]))
    finally:
        lltype.free(value, flavor='raw')

# TODO: uv.ref, uv.unref ?
# TODO: uv.fileno(handle, fd) ?
    
class Stream(Handle):
    def __init__(self, stream):
        self.stream = stream
        self.read_task = None
        self.read_obj = None

        self.read_buf = lltype.nullptr(uv.buf_t)
        self.read_offset = 0
        self.read_nread  = 0

        self.write_task = None
        self.write_obj = None
        self.write_req = uv.malloc_bytes(uv.write_ptr, uv.req_size(uv.WRITE))

        Handle.__init__(self, rffi.cast(uv.handle_ptr, stream))
        self.buffers.append(rffi.cast(rffi.CCHARP, self.write_req))

    def getattr(self, name):
        if name == u"readable":
            return boolean(uv.is_readable(self.stream))
        if name == u"writable":
            return boolean(uv.is_writable(self.stream))
        return Handle.getattr(self, name)

#@Stream.method(u"shutdown", signature(Stream))
#def Stream_shutdown(self):
#    uv.shutdown(shutdown_req, self.stream, Stream_shutdown_cb)
#def Stream_shutdown_cb(shutdown_req, status):
#    pass

#@Stream.method(u"listen", signature(Stream, Integer))
#def Stream_listen(self, backlog):
#    uv.listen(self.stream, backlog.value, Stream_listen_cb)
#def Stream_listen_cb(stream, status):
#    pass

# TODO: uv_accept(server.stream, client.stream) needs some awareness about stream type.

@Stream.method(u"write", signature(Stream, Object))
def Stream_write(self, obj):
    if isinstance(obj, String): # TODO: do this with a cast instead?
        obj = to_uint8array(obj.string.encode('utf-8'))
    elif not isinstance(obj, Uint8Data):
        raise unwind(LError(u"expected a buffer"))

    ec = core.get_ec()
    buf = lltype.malloc(rffi.CArray(uv.buf_t), 1, flavor='raw', zero=True)
    buf[0].c_base = rffi.cast(rffi.CCHARP, obj.uint8data)
    buf[0].c_len = rffi.r_size_t(obj.length)
    try:
        slot = async_begin(self.write_req, ec.uv_writers, (self, obj))
        status = uv.write(self.write_req, self.stream, buf, 1, Stream_write_cb)
        return async_end(ec, slot, self.write_req, ec.uv_writers, status)
    finally:
        lltype.free(buf, flavor='raw')

@jit.dont_look_inside # cast_ptr_to_adr
def Stream_write_cb(write_req, status):
    ec = core.get_ec()
    status = rffi.r_long(status)
    slot, (self, obj) = ec.uv_writers.pop(rffi.cast_ptr_to_adr(write_req))
    if status < 0:
        slot.failure(ec, to_error(status))
    else:
        slot.response(ec, space.null)

# TODO: write2, try_write ?


@Stream.method(u"read", signature(Stream, Uint8Data, optional=1))
def Stream_read(self, block):
    assert self.read_task is None
    if self.read_offset < self.read_nread:
        avail = self.read_nread - self.read_offset
        if block is not None:
            count = min(block.length, avail)
            rffi.c_memcpy(
                rffi.cast(rffi.VOIDP, block.uint8data),
                rffi.ptradd(
                    rffi.cast(rffi.VOIDP, self.read_buf.c_base),
                    self.read_offset),
                count)
            self.read_offset += count
            return Integer(count)
        else:
            builder = StringBuilder()
            builder.append_charpsize(
                rffi.ptradd(self.read_buf.c_base, self.read_offset),
                avail)
            self.read_offset += avail
            return String(builder.build().decode('utf-8'))
    ec = core.get_ec()

    slot = async_begin(self.stream, ec.uv_readers, (self, block))
    status = uv.read_start(self.stream, Stream_alloc_cb, Stream_read_cb)
    return async_end(ec, slot, self.stream, ec.uv_readers, status)

@jit.dont_look_inside # cast_ptr_to_adr
def Stream_alloc_cb(stream, suggested_size, buf):
    ec = core.get_ec()
    slot, (self, block) = ec.uv_readers[rffi.cast_ptr_to_adr(stream)]
    buf.c_base = ptr = lltype.malloc(rffi.CCHARP.TO, suggested_size, flavor='raw')
    buf.c_len = suggested_size
    #assert not self.read_buf, "boom" TODO: this thing leaks memory.
    self.read_buf = buf
    self.buffers.append(ptr)

@jit.dont_look_inside # cast_ptr_to_adr
def Stream_read_cb(stream, nread, buf):
    ec = core.get_ec()
    slot, (self, block) = ec.uv_readers.pop(rffi.cast_ptr_to_adr(stream))
    uv.read_stop(stream)
    if nread < 0:
        slot.failure(ec, to_error(nread))
    elif block is not None:
        count = min(nread, block.length)
        rffi.c_memcpy(
            rffi.cast(rffi.VOIDP, block.uint8data),
            rffi.cast(rffi.VOIDP, buf.c_base),
            count)
        self.read_offset = count
        self.read_avail  = nread
        slot.response(ec, Integer(count))
    else:
        builder = StringBuilder()
        builder.append_charpsize(buf.c_base, nread)
        #TODO: str_decode_utf_8 to handle partial symbols.
        slot.response(ec, String(builder.build().decode('utf-8')))

def initialize_tty(uv_loop, fd, readable):
    handle_type = uv.guess_handle(fd)
    if handle_type == uv.TTY:
        tty = uv.malloc_bytes(uv.tty_ptr, uv.handle_size(uv.TTY))
        check( uv.tty_init(uv_loop, tty, fd, readable) )
        return TTY(tty, fd)
    elif handle_type == uv.NAMED_PIPE:
        pipe = uv.malloc_bytes(uv.pipe_ptr, uv.handle_size(uv.NAMED_PIPE))
        check( uv.pipe_open(pipe, fd) )
        return Pipe(pipe)
    #elif handle_type == uv.FILE:
    else:
        print "unfortunately this std filehandle feature not supported (yet)", str(handle_type)
        return null

# TODO: delete tty/pipe handle when done with it.
class TTY(Stream):
    def __init__(self, tty, fd):
        self.tty = tty
        self.fd = fd
        Stream.__init__(self, rffi.cast(uv.stream_ptr, tty))

@TTY.method(u"set_mode", signature(TTY, String))
def TTY_set_mode(self, modename_obj):
    modename = string_upper(modename_obj.string)
    if modename == u"NORMAL":
        mode = uv.TTY_MODE_NORMAL
    elif modename == u"RAW":
        mode = uv.TTY_MODE_RAW
    elif modename == u"IO":
        mode = uv.TTY_MODE_IO
    else:
        raise unwind(LError(u"unknown mode: " + modename_obj.repr()))
    check( uv.tty_set_mode(self.tty, mode) )
    return null

@TTY.method(u"get_winsize", signature(TTY))
def TTY_get_winsize(self):
    width  = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    height = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.tty_get_winsize(self.tty, width, height) )
        w = rffi.r_long(width[0])
        h = rffi.r_long(height[0])
        return List([Integer(w), Integer(h)])
    finally:
        lltype.free(width, flavor='raw')
        lltype.free(height, flavor='raw')

class Pipe(Stream):
    def __init__(self, pipe):
        self.pipe = pipe

#from interface import Object, null, signature
#


# wait([x, y, z])
# do the same as with .wait(), but prepend the event
# emitter that fires first.


# Left this here for a moment. I'll perhaps need it later.
#     def new_task(self, func, argv):
#         ec = core.get_ec()
#         greenlet = ec.current
#         self.task_count += 1
#         # This side is not aware about task timeouts.
#         with self.task_lock:
#             self.task_queue.append((ec, greenlet, func, argv))
#             if self.task_wait_count > 0:
#                 self.task_wait_lock.release()
#             elif self.worker_quota > 0:
#                 self.worker_quota -= 1
#                 start_new_thread(async_io_thread, ())
#         return core.switch([ec.eventloop])
# 
# ## new starting thread starts and ends without arguments.
# def async_io_thread():
#     rthread.gc_thread_start()
#     async_io_loop(core.g.io)
#     rthread.gc_thread_die()
# 
# def async_io_loop(io):
#     while True:
#         # Checking whether there's task 
#         ec, greenlet, func, argv = None, None, None, []
#         with io.task_lock:
#             if len(io.task_queue) > 0:
#                 ec, greenlet, func, argv = io.task_queue.pop(0)
#             else:
#                 io.task_wait_lock.acquire(False)
#                 io.task_wait_count += 1
#         if func is None:
#             res = acquire_timed(io.task_wait_lock, 10000000) # timeout 10 seconds
#             # Either timeout or release happened.
#             with io.task_lock:
#                 io.task_wait_count -= 1 # we are not waiting for now.
#                 if res == RPY_LOCK_FAILURE and len(io.task_queue) == 0:
#                     io.worker_quota += 1
#                     return # At this point it is very clear that
#                            # this task is no longer needed.
#         else:
#             try:
#                 res = func(argv)
#                 greenlet.argv.append(res)
#             except Unwinder as unwinder:
#                 greenlet.unwinder = unwinder
#             except Exception as exc:
#                 greenlet.unwinder = unwind(LError(
#                     u"Undefined error at async_io_thread(): " +
#                         str(exc).decode('utf-8') + u"\n"))
#             # I hope these are atomic operations.
#             ec.queue.append(greenlet)
#             io.task_count -= 1
#             eventual.et_notify(ec.handle)
# 
# # Taken from pypy
# def acquire_timed(lock, microseconds):
#     """Helper to acquire an interruptible lock with a timeout."""
#     endtime = (time.time() * 1e6) + microseconds
#     while True:
#         result = lock.acquire_timed(microseconds)
#         if result == RPY_LOCK_INTR:
#             # Run signal handlers if we were interrupted
#             # TODO: lever signal handlers?
#             #space.getexecutioncontext().checksignals()
#             if microseconds >= 0:
#                 microseconds = r_longlong((endtime - (time.time() * 1e6))
#                                           + 0.999)
#                 # Check for negative values, since those mean block
#                 # forever
#                 if microseconds <= 0:
#                     result = RPY_LOCK_FAILURE
#         if result != RPY_LOCK_INTR:
#             break
#     return result
# 
# RPY_LOCK_FAILURE, RPY_LOCK_ACQUIRED, RPY_LOCK_INTR = range(3)

# http://docs.libuv.org/en/v1.x/request.html

def check(result):
    if result < 0:
        raise to_error(result)



@specialize.call_location()
@jit.dont_look_inside # cast_ptr_to_adr
def async_begin(handle, table, self):
    adr = rffi.cast_ptr_to_adr(handle)
    if adr in table:
        raise unwind(LError(u"async request collision"))
    slot = Slot(None, None, None)
    table[adr] = (slot, self)
    return slot

@specialize.call_location()
@jit.dont_look_inside # cast_ptr_to_adr
def async_end(ec, slot, handle, table, status):
    adr = rffi.cast_ptr_to_adr(handle)
    if status < 0:
        table.pop(adr)
        raise to_error(status)
    elif slot.result is not None:
        return slot.result
    elif slot.unwind is not None:
        raise slot.unwind
    else:
        slot.greenlet = ec.current
        return core.switch([ec.eventloop])

class Slot:
    def __init__(self, result, unwind, greenlet):
        self.result = result
        self.unwind = unwind
        self.greenlet = greenlet

    def failure(self, ec, unwind):
        if self.greenlet is None:
            self.unwind = unwind
        else:
            self.greenlet.unwind = unwind
            core.root_switch(ec, [self.greenlet])

    def response(self, ec, result):
        if self.greenlet is None:
            self.result = result
        else:
            core.root_switch(ec, [self.greenlet, result])

def to_error(result):
    raise unwind(LUVError(
        rffi.charp2str(uv.err_name(result)).decode('utf-8'),
        rffi.charp2str(uv.strerror(result)).decode('utf-8')
    ))



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
    self.callbacks.remove(cb) # Just crashing on problem for now.
    return null
    
@Event.method(u"wait", signature(Event)) # TODO: with timeout perhaps?
def Event_wait(self):
    ec = core.get_ec()
    self.waiters.append(ec.current)
    return core.switch([ec.eventloop])

for name, obj in {
    u"Event": Event.interface,
    u"TTY": TTY.interface,
    u"Pipe": Pipe.interface,
        }.items():
    base.module.setattr_force(name, obj)

