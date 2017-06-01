from rpython.rtyper.lltypesystem import rffi, lltype
from async_io import *
import rlibuv as uv
import core
import uv_callback
import uv_util

# TODO: Upgrade the stuff to Handle2 as you go. Once done, remove the old Handle

# TODO: It would very much make sense to make certain things actual queues
#       and event handles, then expose them.
#       For example, now you can .on_close.wait()
#       without actually initiating the close yourself.
#       This is potentially useful for anything that ends up into handles.

# When implementing events for handles, be sure to always wrap
# them into an unwinder catcher and root_unwind.

class Handle2(Object):
    def __init__(self, handle):
        self.handle = handle
        self.closed = False
        self.on_close = Event()
        self.events = [self.on_close]
        core.get_ec().handles.stash(self.handle, self)

    # Must do this check every time something is being done to this handle.
    def check_closed(self):
        if self.closed:
            raise unwind(LError(u"Handle is closed"))

    def getattr(self, name):
        if name == u"active":
            if self.closed:
                return false
            return boolean(uv.is_active(self.handle))
        if name == u"closing":
            if self.closed:
                return true
            return boolean(uv.is_closing(self.handle))
        if name == u"closed":
            return boolean(self.closed)
        if name == u"ref":
            if self.closed:
                return false
            return boolean(uv.has_ref(self.handle))
        if name == u"on_close":
            return self.on_close
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"ref":
            self.check_closed()
            if is_true(value):
                uv.ref(self.handle)
            else:
                uv.unref(self.handle)
            return value
        return Object.setattr(self, name, value)

    def listattr(self):
        listing = Object.listattr(self)
        listing.append(String(u"active"))
        listing.append(String(u"closing"))
        listing.append(String(u"closed"))
        listing.append(String(u"ref"))
        return listing

# All handles are resources and they remain in their
# respective stashes as long as they haven't been closed.
# Automatic close to lose them wouldn't be good at all.
#
# The stashing mechanism should always stash the most
# specific reference to an object.
@Handle2.method(u"close", signature(Handle2))
def Handle2_close(self):
    self.check_closed()
    ec = core.get_ec()
    if uv.is_closing(self.handle) == 0:
        uv.close(self.handle, _on_close_)
    # The call of _on_close_ is always deferred
    # to the next round of the event loop.
    return Event_wait(self.on_close)

def _on_close_(handle):
    ec = core.get_ec()
    self = ec.handles.free(handle)
    self.closed = True
    try:
        Event_dispatch(self.on_close, [])
        for event in self.events:
            Event_close(event)
    except Unwinder as unwinder:
        core.root_unwind(unwinder)

@Handle2.method(u"get_send_buffer_size", signature(Handle2))
def Handle2_get_send_buffer_size(self):
    self.check_closed()
    value = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.send_buffer_size(self.handle, value) )
        return Integer(rffi.r_long(value[0]))
    finally:
        lltype.free(value, flavor='raw')

@Handle2.method(u"get_recv_buffer_size", signature(Handle2))
def Handle2_get_recv_buffer_size(self):
    self.check_closed()
    value = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.recv_buffer_size(self.handle, value) )
        return Integer(rffi.r_long(value[0]))
    finally:
        lltype.free(value, flavor='raw')





class Handle(Object):
    def __init__(self, handle):
        self.handle = handle
        self.closed = False

    def getattr(self, name):
        if self.closed:
            raise unwind(LError(u"Handle is closed"))
        if name == u"active":
            if self.closed:
                return false
            return boolean(uv.is_active(self.handle))
        if name == u"closing":
            if self.closed:
                return true
            return boolean(uv.is_closing(self.handle))
        if name == u"closed":
            return boolean(self.closed)
        if name == u"ref":
            if self.closed:
                return false
            return boolean(uv.has_ref(self.handle))
        return Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"ref":
            self.check_closed()
            if is_true(value):
                uv.ref(self.handle)
            else:
                uv.unref(self.handle)
            return value
        return Object.setattr(self, name, value)

    def check_closed(self):
        if self.closed:
            raise unwind(LError(u"Handle is closed"))

    # All handles are resources, so I don't think doing
    # automatic close on losing them would do any good.
    # Besides, some handles have to override the .close

@Handle.method(u"close", signature(Handle))
def Handle_close(self):
    self.check_closed()
    response = uv_callback.close(self.handle)
    uv.close(self.handle, uv_callback.close.cb)
    response.wait()
    self.closed = True
    if self.handle:
        lltype.free(self.handle, flavor='raw')
        self.handle = lltype.nullptr(uv.handle_ptr.TO)
    return null

@Handle.method(u"get_send_buffer_size", signature(Handle))
def Handle_get_send_buffer_size(self):
    self.check_closed()
    value = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.send_buffer_size(self.handle, value) )
        return Integer(rffi.r_long(value[0]))
    finally:
        lltype.free(value, flavor='raw')

@Handle.method(u"get_recv_buffer_size", signature(Handle))
def Handle_get_recv_buffer_size(self):
    self.check_closed()
    value = lltype.malloc(rffi.INTP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.recv_buffer_size(self.handle, value) )
        return Integer(rffi.r_long(value[0]))
    finally:
        lltype.free(value, flavor='raw')

#TODO: think about the name.
@Handle.method(u"get_fileno", signature(Handle))
def Handle_get_fileno(self):
    fd = lltype.malloc(rffi.LONGP.TO, 1, flavor='raw', zero=True)
    try:
        check( uv.fileno(self.handle, fd) )
        return Integer(rffi.r_long(fd[0]))
    finally:
        lltype.free(fd, flavor='raw')

def check(result):
    if rffi.r_long(result) < 0:
        raise uv_callback.to_error(result)
