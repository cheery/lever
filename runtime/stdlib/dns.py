from rpython.rtyper.lltypesystem import rffi, lltype
import pathobj
from space import *
import rlibuv as uv
from uv_handle import check
import uv_callback

module = Module(u'dns', {}, frozen=True)

# TODO: add signature here.
def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

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
            entry.setattr(u"addr", copy_to_uint8array(this.c_ai_addr, this.c_ai_addrlen))
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
@signature(Uint8Array, Integer, optional=1)
def getnameinfo(addr, flags):
    flags = 0 if flags is None else flags.value
    req = lltype.malloc(uv.getnameinfo_ptr.TO, flavor='raw', zero=True)
    sockaddr = array2sockaddr(addr)
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
        lltype.free(sockaddr, flavor='raw')

@builtin
@signature(String, Integer)
def ip4_addr(address, port):
    res = alloc_uint8array(rffi.sizeof(uv.sockaddr_ptr.TO))
    check( uv.ip4_addr( address.string.encode('utf-8'), port.value, res.uint8data) )
    return res

@builtin
@signature(String, Integer)
def ip6_addr(address, port):
    res = alloc_uint8array(rffi.sizeof(uv.sockaddr_ptr.TO))
    check( uv.ip6_addr( address.string.encode('utf-8'), port.value, res.uint8data) )
    return res

@builtin
@signature(Uint8Array)
def ip4_name(array):
    res_length = uv.INET6_ADDRSTRLEN
    res = lltype.malloc(rffi.CCHARP.TO, res_length, flavor="raw")
    sockaddr = array2sockaddr(array)
    try:
        check( uv.ip4_name(sockaddr, res, res_length) )
        return from_cstring(rffi.charp2str(res))
    finally:
        lltype.free(sockaddr, flavor='raw')
        lltype.free(res, flavor='raw')

@builtin
@signature(Uint8Array)
def ip6_name(array):
    res_length = uv.INET6_ADDRSTRLEN
    res = lltype.malloc(rffi.CCHARP.TO, res_length, flavor="raw")
    sockaddr = array2sockaddr(array)
    try:
        check( uv.ip6_name(sockaddr, res, res_length) )
        return from_cstring(rffi.charp2str(res))
    finally:
        lltype.free(sockaddr, flavor='raw')
        lltype.free(res, flavor='raw')

@builtin
@signature(Integer, Uint8Array)
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

def array2sockaddr(array):
    sockaddr = lltype.malloc(uv.sockaddr_ptr.TO, flavor='raw', zero=True)
    rffi.c_memcpy(
        rffi.cast(rffi.VOIDP, sockaddr),
        rffi.cast(rffi.VOIDP, array.uint8data), min(array.length, rffi.sizeof(uv.sockaddr_ptr.TO)))
    return sockaddr

module.setattr_force(u"AF_INET", Integer(uv.AF_INET))
module.setattr_force(u"AF_INET6", Integer(uv.AF_INET6))
