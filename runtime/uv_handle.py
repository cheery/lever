from rpython.rtyper.lltypesystem import rffi, lltype
from space import *
import rlibuv as uv
import core
import uv_callback

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

# TODO: uv.fileno(handle, fd) ?

def check(result):
    if rffi.r_long(result) < 0:
        raise uv_callback.to_error(result)
