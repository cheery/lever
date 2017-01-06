@uv_callback.response
def stream_read_req(a, b, uv_stuff):
    return value

req = stream_read_req(handle, a, b)
return req.wait( uv.some_function(stream_read_req.cb) )


def response(cb):
    name = "uv_" + cb.__name__
    assert name not in uv_init_list
    uv_init_list.append(name)

    @jit.dont_look_inside
    def push_handle(ec, handle, req):
        adr = rffi.cast_ptr_to_adr(handle)
        if adr in table:
            raise unwind(LError(u"async request collision"))
        getattr(ec, name)[adr] = req

    @jit.dont_look_inside
    def pop_handle(ec, handle):
        return getattr(ec, name).pop(
            rffi.cast_ptr_to_adr(handle))

    def _callback_(handle, *uv_stuff):
        ec = main.get_ec()
        req = pop_handle(ec.this_table, handle)
        try:
            val = cb(*(req.data + uv_stuff))
        except Unwinder as unwinder:
            req.failure(unwinder)
        else:
            req.response(val)


    class Request:
        cb = _callback_
        def __init__(self, handle, *data):
            self.ec = main.get_ec()
            self.data = data
            push_handle(ec, handle, self)

        def wait(self, status):
            pass

    return Request
