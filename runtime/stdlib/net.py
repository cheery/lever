from rpython.rtyper.lltypesystem import rffi, lltype
import pathobj
from space import *
import rlibuv as uv
from uv_handle import Handle, check
from uv_stream import Stream
import uv_callback
import core

module = Module(u'net', {}, frozen=True)

# TODO: add signature here.
def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

class TCP(Stream):
    def __init__(self, tcp):
        Stream.__init__(self, rffi.cast(uv.stream_ptr, tcp))
        self.tcp = tcp
    
    def new_stream(self):
        return TCP_init([])

@TCP.instantiator2(signature())
def TCP_init():
    ec = core.get_ec()
    tcp = lltype.malloc(uv.tcp_ptr.TO, flavor="raw", zero=True)
    status = uv.tcp_init(ec.uv_loop, tcp)
    if status < 0:
        lltype.free(tcp, flavor="raw")
        raise uv_callback.to_error(status)
    return TCP(tcp)

@TCP.method(u"nodelay", signature(TCP, Boolean))
def TCP_nodelay(self, enable):
    self.check_closed()
    check( uv.tcp_nodelay(self.tcp, 1 if is_true(enable) else 0) )
    return null

@TCP.method(u"keepalive", signature(TCP, Boolean, Integer, optional=1))
def TCP_nodelay(self, enable, delay):
    self.check_closed()
    check( uv.tcp_keepalive(self.tcp,
        1 if is_true(enable) else 0,
        0 if delay is None else delay.value) )
    return null

@TCP.method(u"simultaneous_accepts", signature(TCP, Boolean))
def TCP_nodelay(self, enable):
    self.check_closed()
    check( uv.tcp_simultaneous_accepts(self.tcp, 1 if is_true(enable) else 0) )
    return null

@TCP.method(u"bind", signature(TCP, Uint8Data, Integer, optional=1))
def TCP_bind(self, addr, flags):
    self.check_closed()
    flags = 0 if flags is None else flags.value
    sockaddr = as_sockaddr(addr)
    check( uv.tcp_bind(self.tcp, sockaddr, flags) )
    return null

@TCP.method(u"getsockname", signature(TCP))
def TCP_getsockname(self):
    self.check_closed()
    array = alloc_uint8array(rffi.sizeof(uv.sockaddr_storage))
    namelen = lltype.malloc(rffi.INTP.TO, 1, flavor="raw", zero=True)
    try:
        check( uv.tcp_getsockname(self.tcp,
            as_sockaddr( array ),
            namelen))
    finally:
        lltype.free(namelen, flavor='raw')
    return array

@TCP.method(u"getpeername", signature(TCP))
def TCP_getpeername(self):
    self.check_closed()
    array = alloc_uint8array(rffi.sizeof(uv.sockaddr_storage))
    namelen = lltype.malloc(rffi.INTP.TO, 1, flavor="raw", zero=True)
    try:
        check( uv.tcp_getpeername(self.tcp,
            as_sockaddr( array ),
            namelen))
    finally:
        lltype.free(namelen, flavor='raw')
    return array

@TCP.method(u"connect", signature(Stream, Uint8Data))
def TCP_connect(self, addr):
    self.check_closed()
    req = lltype.malloc(uv.connect_ptr.TO, flavor='raw', zero=True)
    sockaddr = as_sockaddr(addr)
    try:
        response = uv_callback.connect(req)
        check( response.wait( uv.tcp_connect(req, self.tcp,
            sockaddr, uv_callback.connect.cb) )[0] )
        return null
    finally:
        lltype.free(req, flavor='raw')

class UDP(Handle):
    def __init__(self, udp):
        Handle.__init__(self, rffi.cast(uv.handle_ptr, udp))
        self.udp = udp
        self.alloc_buffers = []
        self.read_buffer_size = 0
        self.read_queue = []
        self.read_greenlet = None

@UDP.instantiator2(signature())
def UDP_init():
    ec = core.get_ec()
    udp = lltype.malloc(uv.udp_ptr.TO, flavor="raw", zero=True)
    status = uv.udp_init(ec.uv_loop, udp)
    if status < 0:
        lltype.free(udp, flavor="raw")
        raise uv_callback.to_error(status)
    return UDP(udp)


@UDP.method(u"bind", signature(UDP, Uint8Data, Integer, optional=1))
def UDP_bind(self, addr, flags):
    self.check_closed()
    flags = 0 if flags is None else flags.value
    sockaddr = as_sockaddr(addr)
    check( uv.udp_bind(self.udp, sockaddr, flags) )
    return null


@UDP.method(u"getsockname", signature(UDP))
def UDP_getsockname(self):
    self.check_closed()
    array = alloc_uint8array(rffi.sizeof(uv.sockaddr_storage))
    namelen = lltype.malloc(rffi.INTP.TO, 1, flavor="raw", zero=True)
    try:
        check( uv.udp_getsockname(self.udp,
            as_sockaddr( array ),
            namelen))
    finally:
        lltype.free(namelen, flavor='raw')
    return array

# int uv_udp_set_membership(uv_udp_t* handle, const char* multicast_addr, const char* interface_addr, uv_membership membership)



@UDP.method(u"set_multicast_loop", signature(UDP, Boolean))
def UDP_set_multicast_loop(self, enable):
    self.check_closed()
    check( uv.udp_set_multicast_loop(self.udp, 1 if is_true(enable) else 0) )
    return null

@UDP.method(u"set_multicast_ttl", signature(UDP, Integer))
def UDP_set_multicast_ttl(self, ttl):
    self.check_closed()
    check( uv.udp_set_multicast_ttl(self.udp, ttl.value) )
    return null

# int uv_udp_set_multicast_interface(uv_udp_t* handle, const char* interface_addr)
# Set the multicast interface to send or receive data on.

@UDP.method(u"set_broadcast", signature(UDP, Boolean))
def UDP_set_broadcast(self, on):
    self.check_closed()
    check( uv.udp_set_broadcast(self.udp, 1 if is_true(on) else 0) )
    return null

@UDP.method(u"set_ttl", signature(UDP, Integer))
def UDP_set_ttl(self, ttl):
    self.check_closed()
    check( uv.udp_set_ttl(self.udp, ttl.value) )
    return null

@UDP.method(u"send", signature(UDP, Object, Uint8Data))
def UDP_send(self, data, addr):
    self.check_closed()
    bufs, nbufs = uv_callback.obj2bufs(data)
    req = lltype.malloc(uv.udp_send_ptr.TO, flavor='raw', zero=True)
    sockaddr = as_sockaddr(addr)
    try:
        response = uv_callback.udp_send(req)
        check( response.wait( uv.udp_send(req, self.udp,
            bufs, nbufs, sockaddr, uv_callback.udp_send.cb))[0] )
        return null
    finally:
        lltype.free(bufs, flavor='raw')
        lltype.free(req, flavor='raw')

@UDP.method(u"try_send", signature(UDP, Object, Uint8Data))
def UDP_try_send(self, data, addr):
    self.check_closed()
    bufs, nbufs = uv_callback.obj2bufs(data)
    req = lltype.malloc(uv.udp_send_ptr.TO, flavor='raw', zero=True)
    sockaddr = as_sockaddr(addr)
    try:
        check( uv.udp_try_send(req, self.udp,
            bufs, nbufs, sockaddr, uv_callback.udp_send.cb))
        return null
    finally:
        lltype.free(bufs, flavor='raw')
        lltype.free(req, flavor='raw')

@UDP.method(u"recv", signature(UDP))
def UDP_recv(self):
    self.check_closed()
    ec = core.get_ec()
    if len(self.read_queue) == 0:
        uv_callback.push(ec.uv__udp_recv, self)
        status = uv.udp_recv_start(self.udp, _udp_alloc_callback_, _udp_read_callback_once_)
        if status < 0:
            uv_callback.drop(ec.uv__udp_recv, self.udp)
            raise uv_callback.to_error(status)
    if len(self.read_queue) == 0:
        if self.read_greenlet is not None:
            raise unwind(LError(u"async collision"))
        self.read_greenlet = ec.current
        core.switch([ec.eventloop])
    array, nread, status, addr, flags = self.read_queue.pop(0)
    if nread < 0:
        raise uv_callback.to_error(nread)
    if status < 0:
        raise uv_callback.to_error(status)
    if array is None:
        array = Uint8Slice(lltype.nullptr(rffi.UCHARP.TO), 0, None)
    elif array.length != nread:
        array = array.subslice(nread)
    res = Exnihilo()
    res.setattr(u"data", array)
    res.setattr(u"addr", addr)
    res.setattr(u"flags", Integer(rffi.r_long(flags)))
    return res

def _udp_alloc_callback_(handle, suggested_size, buf):
    ec = core.get_ec()
    self = uv_callback.peek(ec.uv__udp_recv, handle)
    if self.read_buffer_size > 0:
        array = alloc_uint8array(self.read_buffer_size)
    else:
        array = alloc_uint8array(rffi.r_long(suggested_size))
    self.alloc_buffers.append(array)
    buf.c_base = rffi.cast(rffi.CCHARP, array.uint8data)
    buf.c_len = rffi.r_size_t(array.length)

def _udp_read_callback_once_(stream, nread, buf, addr, flags):
    ec = core.get_ec()
    self = uv_callback.drop(ec.uv__udp_recv, stream)
    for array in self.alloc_buffers:
        if rffi.cast(rffi.CCHARP, array.uint8data) == buf.c_base:
            break
    else:
        array = None
    status = uv.udp_recv_stop(stream)
    if addr:
        addr = copy_to_uint8array(
            rffi.cast(rffi.VOIDP, addr),
            rffi.sizeof(uv.sockaddr_storage),
            rffi.sizeof(uv.sockaddr_storage))
    else:
        addr = null
    self.read_queue.append((array, nread, status, addr, flags))
    if self.read_greenlet is not None:
        greenlet, self.read_greenlet = self.read_greenlet, None
        core.root_switch(ec, [greenlet])

module.setattr_force(u"TCP", TCP.interface)
module.setattr_force(u"UDP", UDP.interface)

# http://beej.us/guide/bgnet/output/html/multipage/sockaddr_inman.html
# possibly bad idea to hack them out by force.. But not sure about it.

@builtin
@signature(String, String, optional=2)
def getaddrinfo(node, service):
    req = lltype.malloc(uv.getaddrinfo_ptr.TO, flavor='raw', zero=True)
    if node is None:
        node_string = lltype.nullptr(rffi.CCHARP.TO)
    else:
        node_string = rffi.str2charp(node.string.encode('utf-8'))
    if service is None:
        service_string = lltype.nullptr(rffi.CCHARP.TO)
    else:
        service_string = rffi.str2charp(service.string.encode('utf-8'))
    try:
        response = uv_callback.getaddrinfo(req)
        status, res = response.wait(uv.getaddrinfo(response.ec.uv_loop, req,
            uv_callback.getaddrinfo.cb,
            node_string,
            service_string,
            lltype.nullptr(uv.addrinfo_ptr.TO)))
        if rffi.r_long(status) < 0:
            raise uv_callback.to_error(status)
        this = res
        result = []
        while this != lltype.nullptr(uv.addrinfo_ptr.TO):
            entry = Exnihilo()
            entry.setattr(u"flags", Integer(rffi.r_long(this.c_ai_flags)))
            entry.setattr(u"family", Integer(rffi.r_long(this.c_ai_family)))
            entry.setattr(u"socktype", Integer(rffi.r_long(this.c_ai_socktype)))
            entry.setattr(u"protocol", Integer(rffi.r_long(this.c_ai_protocol)))
            entry.setattr(u"addr", copy_to_uint8array(
                rffi.cast(rffi.VOIDP, this.c_ai_addr),
                this.c_ai_addrlen, rffi.sizeof(uv.sockaddr_storage)))
            if this.c_ai_canonname:
                entry.setattr(u"canonname", from_cstring(rffi.charp2str(this.c_ai_canonname)))
            else:
                entry.setattr(u"canonname", null)
            result.append(entry)
            this = rffi.cast(uv.addrinfo_ptr, this.c_ai_next)
        uv.freeaddrinfo(res)
        return List(result)
    finally:
        if node_string:
            lltype.free(node_string, flavor='raw')
        if service_string:
            lltype.free(service_string, flavor='raw')
        lltype.free(req, flavor='raw')

@builtin
@signature(Uint8Data, Integer, optional=1)
def getnameinfo(addr, flags):
    flags = 0 if flags is None else flags.value
    req = lltype.malloc(uv.getnameinfo_ptr.TO, flavor='raw', zero=True)
    sockaddr = as_sockaddr(addr)
    try:
        response = uv_callback.getnameinfo(req)
        status, hostname, service = response.wait(uv.getnameinfo(response.ec.uv_loop, req,
            uv_callback.getnameinfo.cb, sockaddr, flags))
        if rffi.r_long(status) < 0:
            raise uv_callback.to_error(status)
        return List([
            from_cstring(rffi.charp2str(hostname)),
            from_cstring(rffi.charp2str(service))
        ])
    finally:
        lltype.free(req, flavor='raw')

@builtin
@signature(String, Integer)
def ip4_addr(address, port):
    res = alloc_uint8array(rffi.sizeof(uv.sockaddr_storage))
    check( uv.ip4_addr( address.string.encode('utf-8'), port.value, res.uint8data) )
    return res

@builtin
@signature(String, Integer)
def ip6_addr(address, port):
    res = alloc_uint8array(rffi.sizeof(uv.sockaddr_storage))
    check( uv.ip6_addr( address.string.encode('utf-8'), port.value, res.uint8data) )
    return res

@builtin
@signature(Uint8Data)
def ip4_name(addr):
    res_length = uv.INET6_ADDRSTRLEN
    res = lltype.malloc(rffi.CCHARP.TO, res_length, flavor="raw")
    sockaddr = as_sockaddr(addr)
    try:
        check( uv.ip4_name(sockaddr, res, res_length) )
        return from_cstring(rffi.charp2str(res))
    finally:
        lltype.free(res, flavor='raw')

@builtin
@signature(Uint8Data)
def ip6_name(addr):
    res_length = uv.INET6_ADDRSTRLEN
    res = lltype.malloc(rffi.CCHARP.TO, res_length, flavor="raw")
    sockaddr = as_sockaddr(addr)
    try:
        check( uv.ip6_name(sockaddr, res, res_length) )
        return from_cstring(rffi.charp2str(res))
    finally:
        lltype.free(res, flavor='raw')

@builtin
@signature(Integer, Uint8Data)
def inet_ntop(af, src):
    af = af.value
    if af == uv.AF_INET:
        L = 4
    elif af == uv.AF_INET6:
        L = 16
    else:
        raise unwind(LError(u"first argument must be either AF_INET or AF_INET6"))
    if src.length < L:
        raise unwind(LError(u"argument too short to be an address"))
    res_length = uv.INET6_ADDRSTRLEN
    res = lltype.malloc(rffi.CCHARP.TO, res_length, flavor="raw")
    try:
        check( uv.inet_ntop(af, src.uint8data, res, res_length) )
        return from_cstring(rffi.charp2str(res))
    finally:
        lltype.free(res, flavor='raw')

@builtin
@signature(Integer, String)
def inet_pton(af, src):
    af = af.value
    if af == uv.AF_INET:
        res = alloc_uint8array(4)
    elif af == uv.AF_INET6:
        res = alloc_uint8array(16)
    else:
        raise unwind(LError(u"first argument must be either AF_INET or AF_INET6"))
    check( uv.inet_ntop(af, src.string.encode('utf-8'), res.uint8data) )
    return res

def as_sockaddr(array):
    if array.length != rffi.sizeof(uv.sockaddr_storage):
        raise unwind(LError(u"Sockaddr is expected in length of sockaddr_storage_size"))
    return rffi.cast(uv.sockaddr_ptr, array.uint8data)

def copy_to_uint8array(base, length, storage):
    length = rffi.r_long(length)
    array = alloc_uint8array(storage)
    rffi.c_memcpy(
        rffi.cast(rffi.VOIDP, array.uint8data),
        base, length)
    return array

for name_, const_ in uv.net_constants.items():
    module.setattr_force(name_, Integer(const_))
