from rpython.rlib.objectmodel import specialize
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
import space
import rlibuv as uv

# The concepts behind this nice and tricky stash originate from
# typhon/ruv.py module of the monte language.
# proposed usage:
#   handle_stash = stashFor("handle")
#
#   in the execution context init:
#       ec.handles = handle_stash(uv_loop)
# 
#   in the instantiation of an object:
#       ref = TCP(uv.tcp_ptr, ec.handles.create(uv.tcp_init))
# 
#   class TCP(Handle):
#       def __init__(self, tcp):
#           Handle.__init__(self, rffi.cast(uv.handle_ptr, tcp))
#           self.tcp = tcp
# 
#   somewhere in Handle:
#       ec.handles.stash(self.handle, self)
#     
#       self = ec.handles.free(self.handle)
# 
#   def _tcp_callback_(tcp):
#       ref = ec.handles.get(tcp, TCP)
#
# This stash never shrinks, but the waste is
# expected to be very minor as there is just that many handles
# you desire to use in the first place.
def stashFor(name):
    class stash:
        def __init__(self, uv_loop, initial_size = 4):
            self.uv_loop = uv_loop
            self.freelist = [i for i in range(initial_size)]
            self.storage = [None] * initial_size

        @specialize.arg(1, 2)
        def create(self, ptr, init=dont_init, *args):
            this = lltype.malloc(ptr.TO, flavor="raw", zero=True)
            status = init(self.uv_loop, this, *args)
            if status < 0:
                lltype.free(this, flavor="raw")
                raise to_error(status)
            try:
                index = self.freelist.pop()
            except IndexError:
                extra = len(self.storage)
                self.storage = self.storage + [None] * extra
                for i in range(extra, extra+extra):
                    self.freelist.append(i)
                index = self.freelist.pop()
            this.c_data = rffi.cast(rffi.VOIDP, index)
            return this

        def stash(self, this, ref):
            index = rffi.cast(rffi.INT, this.c_data)
            self.storage[index] = ref

        @specialize.arg(2)
        def get(self, this, spec):
            index = rffi.cast(rffi.INT, this.c_data)
            ref = self.storage[index]
            assert isinstance(ref, spec)
            return ref

        def free(self, this):
            index = rffi.cast(rffi.INT, this.c_data)
            ref, self.storage[index] = self.storage[index], None
            self.freelist.append(index)
            lltype.free(this, flavor="raw")
            return ref

    stash.__name__ = name + "_stash"
    return stash

def check(result):
    if rffi.r_long(result) < 0:
        raise to_error(result)

def to_error(result):
    raise space.unwind(space.LUVError(
        rffi.charp2str(uv.err_name(result)).decode('utf-8'),
        rffi.charp2str(uv.strerror(result)).decode('utf-8')
    ))

def dont_init(uv_loop, this):
    return 0

# TODO: Simplify the uv_callback.response_handler
#       with the above stash, if it turns
#       out as very nice.
