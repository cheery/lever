from rpython.rlib.objectmodel import always_inline, specialize
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import os, sys

stdio_flags = rffi.INT
uv_file = rffi.INT

# recurring pattern, as we do not know the sizes of structures.
@specialize.call_location()
def malloc_bytes(ptr_type, size):
    return rffi.cast(ptr_type,
        lltype.malloc(rffi.CCHARP.TO, size, flavor='raw', zero=True))

@specialize.call_location()
def free(ptr):
    lltype.free(ptr, flavor='raw')

# This is quite a source of frustration.
# 
def envPaths(name):
    val = os.getenv(name)
    return [] if val is None else val.split(':')

eci = ExternalCompilationInfo(
    includes = ["uv.h"], libraries = ["uv"],
    include_dirs=envPaths("DEPENDENCY_INCLUDE_PATH"),
    library_dirs=envPaths("DEPENDENCY_LIBRARY_PATH"))

for t in [rffi.LONG, rffi.LONGLONG]:
    if rffi.sizeof(t) == 8:
        int64_t = t
        break
else:
    assert False, "int64_t not found"
for t in [rffi.ULONG, rffi.ULONGLONG]:
    if rffi.sizeof(t) == 8:
        uint64_t = t
        break
else:
    assert False, "int64_t not found"

handle_type = rffi.INT
(
UNKNOWN_HANDLE,
ASYNC,
CHECK,
FS_EVENT,
FS_POLL,
HANDLE,
IDLE,
NAMED_PIPE,
POLL,
PREPARE,
PROCESS,
STREAM,
TCP,
TIMER,
TTY,
UDP,
SIGNAL,
FILE,
HANDLE_TYPE_MAX
) = range(19)

req_type = rffi.INT
(
UNKNOWN_REQ,
REQ,
CONNECT,
WRITE,
SHUTDOWN,
UDP_SEND,
FS,
WORK,
GETADDRINFO,
GETNAMEINFO,
REQ_TYPE_PRIVATE,
REQ_TYPE_MAX
) = range(12)

error_names = [
    "E2BIG", "EACCES", "EADDRINUSE", "EADDRNOTAVAIL", "EAFNOSUPPORT",
    "EAGAIN", "EAI_ADDRFAMILY", "EAI_AGAIN", "EAI_BADFLAGS",
    "EAI_BADHINTS", "EAI_CANCELED", "EAI_FAIL", "EAI_FAMILY",
    "EAI_MEMORY", "EAI_NODATA", "EAI_NONAME", "EAI_OVERFLOW",
    "EAI_PROTOCOL", "EAI_SERVICE", "EAI_SOCKTYPE", "EALREADY",
    "EBADF", "EBUSY", "ECANCELED", "ECHARSET", "ECONNABORTED",
    "ECONNREFUSED", "ECONNRESET", "EDESTADDRREQ", "EEXIST", "EFAULT",
    "EFBIG", "EHOSTDOWN", "EHOSTUNREACH", "EINTR", "EINVAL", "EIO",
    "EISCONN", "EISDIR", "ELOOP", "EMFILE", "EMLINK", "EMSGSIZE",
    "ENAMETOOLONG", "ENETDOWN", "ENETUNREACH", "ENFILE", "ENOBUFS",
    "ENODEV", "ENOENT", "ENOMEM", "ENONET", "ENOPROTOOPT", "ENOSPC",
    "ENOSYS", "ENOTCONN", "ENOTDIR", "ENOTEMPTY", "ENOTSOCK",
    "ENOTSUP", "ENXIO", "EOF", "EPERM", "EPIPE", "EPROTO",
    "EPROTONOSUPPORT", "EPROTOTYPE", "ERANGE", "EROFS", "ESHUTDOWN",
    "ESPIPE", "ESRCH", "ETIMEDOUT", "ETXTBSY", "EXDEV", "UNKNOWN",
]

exit_cb_arg0 = lltype.Ptr(lltype.ForwardReference())
exit_cb = rffi.CCallback([exit_cb_arg0, int64_t, rffi.INT],      lltype.Void)

class CConfig:
    _compilation_info_ = eci

    timespec_t = rffi_platform.Struct("uv_timespec_t", [
        ("tv_sec",  rffi.LONG),
        ("tv_nsec", rffi.LONG)])

    stat_t = rffi_platform.Struct("uv_stat_t", [
        ("st_dev",      uint64_t  ),
        ("st_mode",     uint64_t  ),
        ("st_nlink",    uint64_t  ),
        ("st_uid",      uint64_t  ),
        ("st_gid",      uint64_t  ),
        ("st_rdev",     uint64_t  ),
        ("st_ino",      uint64_t  ),
        ("st_size",     uint64_t  ),
        ("st_blksize",  uint64_t  ),
        ("st_blocks",   uint64_t  ),
        ("st_flags",    uint64_t  ),
        ("st_gen",      uint64_t  ),
        ("st_atim",     timespec_t),
        ("st_mtim",     timespec_t),
        ("st_ctim",     timespec_t),
        ("st_birthtim", timespec_t)])

    #dirent_type_t = rffi_platform.SimpleType("uv_dirent_type_t", rffi.INT)
    dirent_t = rffi_platform.Struct("uv_dirent_t", [
        ("name", rffi.CCHARP),
        ("type", rffi.INT)])

    sockaddr = rffi_platform.Struct("struct sockaddr", [
        ("sa_family", rffi.USHORT)])

    handle_t = rffi_platform.Struct("uv_handle_t", [("data", rffi.VOIDP)])
    stream_t = rffi_platform.Struct("uv_stream_t", [("data", rffi.VOIDP)])
    tcp_t    = rffi_platform.Struct("uv_tcp_t",    [("data", rffi.VOIDP)])
    udp_t    = rffi_platform.Struct("uv_udp_t",    [("data", rffi.VOIDP)])
    pipe_t   = rffi_platform.Struct("uv_pipe_t",   [("data", rffi.VOIDP)])
    tty_t    = rffi_platform.Struct("uv_tty_t",    [("data", rffi.VOIDP)])
    poll_t   = rffi_platform.Struct("uv_poll_t",   [("data", rffi.VOIDP)])
    timer_t  = rffi_platform.Struct("uv_timer_t",  [("data", rffi.VOIDP)])
    prepare_t = rffi_platform.Struct("uv_prepare_t", [("data", rffi.VOIDP)])
    check_t   = rffi_platform.Struct("uv_check_t",   [("data", rffi.VOIDP)])
    idle_t    = rffi_platform.Struct("uv_idle_t",    [("data", rffi.VOIDP)])
    async_t   = rffi_platform.Struct("uv_async_t",   [("data", rffi.VOIDP)])
    process_t = rffi_platform.Struct("uv_process_t", [
        ("data", rffi.VOIDP),
        ("pid",  rffi.INT)])

    uid_t = rffi_platform.SimpleType("uv_uid_t", rffi.ULONG)
    gid_t = rffi_platform.SimpleType("uv_gid_t", rffi.ULONG)

    # the rffi of rpython doesn't seem to support unions.
    stdio_container_t = rffi_platform.Struct("uv_stdio_container_t", [
        ("flags", stdio_flags)])

    #loop_t = rffi_platform.Struct("uv_loop_t", [("data", rffi.VOIDP)])
    process_options_t = rffi_platform.Struct("uv_process_options_t", [
        ("exit_cb", exit_cb),
        ("file", rffi.CCHARP),
        ("args", rffi.CCHARPP),
        ("env", rffi.CCHARPP),
        ("cwd", rffi.CCHARP),
        ("flags", rffi.UINT),
        ("stdio_count", rffi.INT),
        ("stdio", lltype.Ptr(lltype.ForwardReference())),
        ("uid", rffi.ULONG),
        ("gid", rffi.ULONG)])

    connect_t  = rffi_platform.Struct("uv_connect_t",  [("data", rffi.VOIDP)])
    udp_send_t = rffi_platform.Struct("uv_udp_send_t", [("data", rffi.VOIDP)])
    #                                 [("handle",
    #                                   lltype.Ptr(lltype.ForwardReference()))])
    #shutdown_t = rffi_platform.Struct("uv_shutdown_t", [])
    fs_event_t  = rffi_platform.Struct("uv_fs_event_t", [("data", rffi.VOIDP)])
    fs_poll_t   = rffi_platform.Struct("uv_fs_poll_t",  [("data", rffi.VOIDP)])
    signal_t    = rffi_platform.Struct("uv_signal_t",   [("data", rffi.VOIDP)])

    shutdown_t = rffi_platform.Struct("uv_shutdown_t", [("data", rffi.VOIDP)])
    write_t = rffi_platform.Struct("uv_write_t", [("data", rffi.VOIDP)])

    fs_t = rffi_platform.Struct("uv_fs_t", [
        ("data", rffi.VOIDP),
        ("path", rffi.CONST_CCHARP),
        ("result", rffi.SSIZE_T),
        ("statbuf", stat_t),
        ("ptr", rffi.VOIDP)])
    uv_getaddrinfo_t = rffi_platform.Struct("uv_getaddrinfo_t", [("data", rffi.VOIDP)])
    uv_getnameinfo_t = rffi_platform.Struct("uv_getnameinfo_t", [("data", rffi.VOIDP)])
    buf_t = rffi_platform.Struct("uv_buf_t", [
        ("base", rffi.CCHARP),
        ("len", rffi.SIZE_T)])

    sockaddr_storage = rffi_platform.Struct("struct sockaddr_storage", [])
    addrinfo = rffi_platform.Struct("struct addrinfo", [
        ("ai_flags", rffi.INT),
        ("ai_family", rffi.INT),
        ("ai_socktype", rffi.INT),
        ("ai_protocol", rffi.INT),
        ("ai_addrlen", rffi.SIZE_T),
        ("ai_addr", rffi.VOIDP), # struct sockaddr*
        ("ai_canonname", rffi.CCHARP),
        ("ai_next", rffi.VOIDP),
    ])

    UV_EOF = rffi_platform.ConstantInteger("UV_EOF")
    UV_ECANCELED = rffi_platform.ConstantInteger("UV_ECANCELED")

    AF_UNSPEC = rffi_platform.ConstantInteger("AF_UNSPEC")
    AF_INET = rffi_platform.ConstantInteger("AF_INET")
    AF_INET6 = rffi_platform.ConstantInteger("AF_INET6")
    SOCK_STREAM = rffi_platform.ConstantInteger("SOCK_STREAM")
    SOCK_DGRAM = rffi_platform.ConstantInteger("SOCK_DGRAM")
    AI_V4MAPPED = rffi_platform.ConstantInteger("AI_V4MAPPED")
    AI_ADDRCONFIG = rffi_platform.ConstantInteger("AI_ADDRCONFIG")
    AI_NUMERICHOST = rffi_platform.ConstantInteger("AI_NUMERICHOST")
    AI_PASSIVE = rffi_platform.ConstantInteger("AI_PASSIVE")
    #TCP_IPV6ONLY = rffi_platform.ConstantInteger("TCP_IPV6ONLY")
    AI_NUMERICHOST = rffi_platform.ConstantInteger("AI_NUMERICHOST")
    AI_PASSIVE = rffi_platform.ConstantInteger("AI_PASSIVE")
    INADDR_ANY = rffi_platform.ConstantInteger("INADDR_ANY")
    #IN6ADDR_ANY_INIT = rffi_platform.ConstantInteger("IN6ADDR_ANY_INIT")
    INADDR_LOOPBACK = rffi_platform.ConstantInteger("INADDR_LOOPBACK")
    #IN6ADDR_LOOPBACK_INIT = rffi_platform.ConstantInteger("IN6ADDR_LOOPBACK_INIT")
    AI_NUMERICSERV = rffi_platform.ConstantInteger("AI_NUMERICSERV")
    AI_CANONNAME = rffi_platform.ConstantInteger("AI_CANONNAME")
    AI_IDN = rffi_platform.ConstantInteger("AI_IDN")
    AI_CANONIDN = rffi_platform.ConstantInteger("AI_CANONIDN")
    AI_IDN_ALLOW_UNASSIGNED = rffi_platform.ConstantInteger("AI_IDN_ALLOW_UNASSIGNED")
    AI_IDN_USE_STD3_ASCII_RULES = rffi_platform.ConstantInteger("AI_IDN_USE_STD3_ASCII_RULES")
    NI_NAMEREQD = rffi_platform.ConstantInteger("NI_NAMEREQD")
    NI_DGRAM = rffi_platform.ConstantInteger("NI_DGRAM")
    NI_NOFQDN = rffi_platform.ConstantInteger("NI_NOFQDN")
    NI_NUMERICHOST = rffi_platform.ConstantInteger("NI_NUMERICHOST")
    NI_NUMERICSERV = rffi_platform.ConstantInteger("NI_NUMERICSERV")
    NI_IDN = rffi_platform.ConstantInteger("NI_IDN")
    NI_IDN_ALLOW_UNASSIGNED = rffi_platform.ConstantInteger("NI_IDN_ALLOW_UNASSIGNED")
    NI_IDN_USE_STD3_ASCII_RULES = rffi_platform.ConstantInteger("NI_IDN_USE_STD3_ASCII_RULES")

    INET6_ADDRSTRLEN = rffi_platform.ConstantInteger("INET6_ADDRSTRLEN")

    # Add _ in front if these aren't on the Win32
    O_RDONLY = rffi_platform.ConstantInteger("O_RDONLY")
    O_WRONLY = rffi_platform.ConstantInteger("O_WRONLY")
    O_RDWR = rffi_platform.ConstantInteger("O_RDWR")
    O_APPEND = rffi_platform.ConstantInteger("O_APPEND")
    O_CREAT = rffi_platform.ConstantInteger("O_CREAT")
    O_EXCL = rffi_platform.ConstantInteger("O_EXCL")
    O_TRUNC = rffi_platform.ConstantInteger("O_TRUNC")

    for name in error_names:
        locals()[name] = rffi_platform.ConstantInteger("UV_"+name)

cConfig = rffi_platform.configure(CConfig)

errors = dict(
    (cConfig[name], name)
    for name in error_names)

uid_t = cConfig['uid_t']
gid_t = cConfig['gid_t']

stat_t = cConfig['stat_t']
buf_t = cConfig['buf_t']

EOF = cConfig['UV_EOF']
ECANCELED = cConfig['UV_ECANCELED']

AF_INET = cConfig['AF_INET']
AF_INET6 = cConfig['AF_INET6']

net_constants = {
    u"AF_UNSPEC": cConfig['AF_UNSPEC'],
    u"AF_INET": cConfig['AF_INET'],
    u"AF_INET6": cConfig['AF_INET6'],
#    u"TCP_IPV6ONLY": cConfig['TCP_IPV6ONLY'],
    u"SOCK_STREAM": cConfig['SOCK_STREAM'],
    u"SOCK_DGRAM": cConfig['SOCK_DGRAM'],
    u"AI_V4MAPPED": cConfig['AI_V4MAPPED'],
    u"AI_ADDRCONFIG": cConfig['AI_ADDRCONFIG'],
    u"AI_NUMERICHOST": cConfig["AI_NUMERICHOST"],
    u"AI_PASSIVE": cConfig["AI_PASSIVE"],
    u"INADDR_ANY": cConfig["INADDR_ANY"],
#    u"IN6ADDR_ANY_INIT": cConfig["IN6ADDR_ANY_INIT"],
    u"INADDR_LOOPBACK": cConfig["INADDR_LOOPBACK"],
#    u"IN6ADDR_LOOPBACK_INIT": cConfig["IN6ADDR_LOOPBACK_INIT"],
    u"AI_NUMERICSERV": cConfig["AI_NUMERICSERV"],
    u"AI_CANONNAME": cConfig["AI_CANONNAME"],
    u"AI_IDN": cConfig["AI_IDN"],
    u"AI_CANONIDN": cConfig["AI_CANONIDN"],
    u"AI_IDN_ALLOW_UNASSIGNED": cConfig["AI_IDN_ALLOW_UNASSIGNED"],
    u"AI_IDN_USE_STD3_ASCII_RULES": cConfig["AI_IDN_USE_STD3_ASCII_RULES"],
    u"NI_NAMEREQD": cConfig["NI_NAMEREQD"],
    u"NI_DGRAM": cConfig["NI_DGRAM"],
    u"NI_NOFQDN": cConfig["NI_NOFQDN"],
    u"NI_NUMERICHOST": cConfig["NI_NUMERICHOST"],
    u"NI_NUMERICSERV": cConfig["NI_NUMERICSERV"],
    u"NI_IDN": cConfig["NI_IDN"],
    u"NI_IDN_ALLOW_UNASSIGNED": cConfig["NI_IDN_ALLOW_UNASSIGNED"],
    u"NI_IDN_USE_STD3_ASCII_RULES": cConfig["NI_IDN_USE_STD3_ASCII_RULES"],
    u"UDP_IPV6ONLY": 1,
    u"UDP_PARTIAL": 2,
    u"UDP_REUSEADDR": 4,
    u"UDP_LEAVE_GROUP": 0,
    u"UDP_JOIN_GROUP": 1,
}

INET6_ADDRSTRLEN = cConfig['INET6_ADDRSTRLEN']

file_flags = {
    u"RDONLY": cConfig['O_RDONLY'],
    u"WRONLY": cConfig['O_WRONLY'],
    u"RDWR": cConfig['O_RDWR'],
    u"APPEND": cConfig['O_APPEND'],
    u"CREAT": cConfig['O_CREAT'],
    u"EXCL": cConfig['O_EXCL'],
    u"TRUNC": cConfig['O_TRUNC'],
}


dirent_ptr = lltype.Ptr(cConfig["dirent_t"])

# Handle types
loop_ptr = rffi.COpaquePtr("uv_loop_t")
handle_ptr  = lltype.Ptr(cConfig["handle_t"])
stream_ptr  = lltype.Ptr(cConfig["stream_t"])
tcp_ptr     = lltype.Ptr(cConfig["tcp_t"])
udp_ptr     = lltype.Ptr(cConfig["udp_t"])
pipe_ptr    = lltype.Ptr(cConfig["pipe_t"])
tty_ptr     = lltype.Ptr(cConfig["tty_t"])
poll_ptr    = lltype.Ptr(cConfig["poll_t"])
timer_ptr   = lltype.Ptr(cConfig["timer_t"])
prepare_ptr = lltype.Ptr(cConfig["prepare_t"])
check_ptr   = lltype.Ptr(cConfig["check_t"])
idle_ptr    = lltype.Ptr(cConfig["idle_t"])
async_ptr   = lltype.Ptr(cConfig["async_t"])
process_ptr = lltype.Ptr(cConfig["process_t"])

fs_event_ptr = lltype.Ptr(cConfig["fs_event_t"])
fs_poll_ptr  = lltype.Ptr(cConfig["fs_poll_t"])

signal_ptr = lltype.Ptr(cConfig["signal_t"])

# Request types
req_ptr = rffi.COpaquePtr("uv_req_t")

getaddrinfo_ptr = lltype.Ptr(cConfig["uv_getaddrinfo_t"])
getnameinfo_ptr = lltype.Ptr(cConfig["uv_getnameinfo_t"])

shutdown_ptr = lltype.Ptr(cConfig["shutdown_t"])
write_ptr = lltype.Ptr(cConfig["write_t"])
connect_ptr = lltype.Ptr(cConfig["connect_t"])
udp_send_ptr = lltype.Ptr(cConfig["udp_send_t"])
fs_ptr = lltype.Ptr(cConfig["fs_t"])
work_ptr = rffi.COpaquePtr("uv_work_t")

# None of the above
cpu_info_ptr = rffi.COpaquePtr("uv_cpu_info_t")
interface_address_ptr = rffi.COpaquePtr("uv_interface_address_t")
passwd_ptr = rffi.COpaquePtr("uv_passwd_t")

#LOOP_BLOCK_SIGNAL = 0

run_mode = rffi.INT
RUN_DEFAULT = 0
RUN_ONCE = 1
RUN_NOWAIT = 2

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result,
        compilation_info=eci, **kwds)

version = llexternal("uv_version", [], rffi.INT)
version_string = llexternal("uv_version_string", [], rffi.CCHARP)

malloc_func  = rffi.CCallback([rffi.SIZE_T], rffi.VOIDP)
realloc_func = rffi.CCallback([rffi.VOIDP,  rffi.SIZE_T], rffi.VOIDP)
calloc_func  = rffi.CCallback([rffi.SIZE_T, rffi.SIZE_T], rffi.VOIDP)
free_func    = rffi.CCallback([rffi.VOIDP], lltype.Void)

replace_allocator = llexternal("uv_replace_allocator",
    [malloc_func, realloc_func, calloc_func, free_func], 
    rffi.INT)

default_loop = llexternal("uv_default_loop", [], loop_ptr)

loop_init  = llexternal("uv_loop_init",  [loop_ptr], rffi.INT)
loop_close = llexternal("uv_loop_close", [loop_ptr], rffi.INT)

loop_size = llexternal("uv_loop_size", [], rffi.SIZE_T)

loop_alive = llexternal("uv_loop_alive", [loop_ptr], rffi.INT)

# consider a hack if you use this one.
#loop_configure = llexternal("uv_loop_configure", [loop_ptr, loop_option, ...], rffi.INT)

run  = llexternal("uv_run",  [loop_ptr, run_mode], rffi.INT)
stop = llexternal("uv_stop", [loop_ptr], lltype.Void)

ref     = llexternal("uv_ref",     [handle_ptr], lltype.Void)
unref   = llexternal("uv_unref",   [handle_ptr], lltype.Void)
has_ref = llexternal("uv_has_ref", [handle_ptr], rffi.INT)

update_time = llexternal("uv_update_time", [loop_ptr], lltype.Void)
now         = llexternal("uv_now",         [loop_ptr], uint64_t)

# probably won't need these.
# UV_EXTERN int uv_backend_fd(const uv_loop_t*);
# UV_EXTERN int uv_backend_timeout(const uv_loop_t*);

# I got no idea why this detail had to be exposed like this....
if sys.platform != "win32":
#    buf_t = lltype.Struct("uv_buf_t",
#        ("base", rffi.CCHARP),
#        ("size", rffi.SIZE_T))
    os_sock_t = rffi.INT
else:
#    buf_t = lltype.Struct("uv_buf_t",
#        ("size", rffi.SIZE_T), # or ULONG
#        ("base", rffi.CCHARP))
    os_sock_t = rffi.VOIDP

sockaddr = cConfig["sockaddr"]
sockaddr_ptr = lltype.Ptr(sockaddr)

buf_ptr = lltype.Ptr(buf_t)
alloc_cb = rffi.CCallback([handle_ptr, rffi.SIZE_T, buf_ptr], lltype.Void)
read_cb  = rffi.CCallback([stream_ptr, rffi.SSIZE_T, buf_ptr], lltype.Void)

write_cb       = rffi.CCallback([write_ptr,      rffi.INT],               lltype.Void)
connect_cb     = rffi.CCallback([connect_ptr,    rffi.INT],               lltype.Void)
shutdown_cb    = rffi.CCallback([shutdown_ptr,   rffi.INT],               lltype.Void)
connection_cb  = rffi.CCallback([stream_ptr,     rffi.INT],               lltype.Void)
close_cb       = rffi.CCallback([handle_ptr],                             lltype.Void)
poll_cb        = rffi.CCallback([poll_ptr,       rffi.INT, rffi.INT],     lltype.Void)
timer_cb       = rffi.CCallback([timer_ptr],                              lltype.Void)
async_cb       = rffi.CCallback([async_ptr],                              lltype.Void)
prepare_cb     = rffi.CCallback([prepare_ptr],                            lltype.Void)
check_cb       = rffi.CCallback([check_ptr],                              lltype.Void)
idle_cb        = rffi.CCallback([idle_ptr],                               lltype.Void)
exit_cb_arg0.TO.become(process_ptr.TO)
walk_cb        = rffi.CCallback([handle_ptr,     rffi.VOIDP],             lltype.Void)
fs_cb          = rffi.CCallback([fs_ptr],                                 lltype.Void)
work_cb        = rffi.CCallback([work_ptr],                               lltype.Void)
after_work_cb  = rffi.CCallback([work_ptr,       rffi.INT],               lltype.Void)

sockaddr_storage = cConfig["sockaddr_storage"]
addrinfo_ptr = lltype.Ptr(cConfig["addrinfo"])

getaddrinfo_cb = rffi.CCallback([getaddrinfo_ptr, rffi.INT, addrinfo_ptr], lltype.Void)
getnameinfo_cb = rffi.CCallback([getnameinfo_ptr, rffi.INT, rffi.CCHARP, rffi.CCHARP], lltype.Void)

fs_event_cb = rffi.CCallback([fs_event_ptr, rffi.CCHARP, rffi.INT, rffi.INT], lltype.Void)
fs_poll_cb  = rffi.CCallback([fs_poll_ptr, rffi.INT, lltype.Ptr(stat_t), lltype.Ptr(stat_t)], lltype.Void)
signal_cb   = rffi.CCallback([signal_ptr, rffi.INT], lltype.Void)

stdio_container_t = cConfig["stdio_container_t"]
cConfig["process_options_t"].c_stdio.TO.become(
    lltype.Array(stdio_container_t, hints={"nolength": True}))
stdio_container_ptr = lltype.Ptr(stdio_container_t)
process_options_ptr = lltype.Ptr(cConfig["process_options_t"])

membership = rffi.INT
# uv_membership
LEAVE_GROUP = 0
JOIN_GROUP = 1

translate_sys_error = llexternal("uv_translate_sys_error", [rffi.INT], rffi.INT)
strerror = llexternal("uv_strerror", [rffi.INT], rffi.CCHARP)
err_name = llexternal("uv_err_name", [rffi.INT], rffi.CCHARP)

shutdown = llexternal("uv_shutdown", [shutdown_ptr, stream_ptr, shutdown_cb], rffi.INT)

handle_size = llexternal("uv_handle_size", [handle_type], rffi.SIZE_T)
req_size    = llexternal("uv_req_size",    [req_type], rffi.SIZE_T)

is_active   = llexternal("uv_is_active",   [handle_ptr], rffi.INT)

walk        = llexternal("uv_walk",        [loop_ptr, walk_cb, rffi.VOIDP], lltype.Void)

# /* Helpers for ad hoc debugging, no API/ABI stability guaranteed. */
# UV_EXTERN void uv_print_all_handles(uv_loop_t* loop, FILE* stream);
# UV_EXTERN void uv_print_active_handles(uv_loop_t* loop, FILE* stream);
 
close       = llexternal("uv_close",       [handle_ptr, close_cb], lltype.Void)

send_buffer_size = llexternal("uv_send_buffer_size", [handle_ptr, rffi.INTP], rffi.INT)
recv_buffer_size = llexternal("uv_recv_buffer_size", [handle_ptr, rffi.INTP], rffi.INT)

os_fd_t = rffi.LONGP
fileno = llexternal("uv_fileno", [handle_ptr, os_fd_t], rffi.INT)
# UV_EXTERN int uv_fileno(const uv_handle_t* handle, uv_os_fd_t* fd);
 
#def buf_init(uv_buf, base, length):
#    uv_buf
#buf_init = llexternal("uv_buf_init", [rffi.CCHARP, rffi.UINT], buf_t)

listen = llexternal("uv_listen", [stream_ptr, rffi.INT, connection_cb], rffi.INT)
accept = llexternal("uv_accept", [stream_ptr, stream_ptr], rffi.INT)

read_start = llexternal("uv_read_start", [stream_ptr, alloc_cb, read_cb], rffi.INT)
read_stop  = llexternal("uv_read_stop",  [stream_ptr], rffi.INT)

write = llexternal("uv_write", [write_ptr, stream_ptr, rffi.CArrayPtr(buf_t), rffi.UINT, write_cb], rffi.INT)
write2 = llexternal("uv_write2", [write_ptr, stream_ptr, rffi.CArrayPtr(buf_t), rffi.UINT, stream_ptr, write_cb], rffi.INT)
try_write = llexternal("uv_try_write", [stream_ptr, rffi.CArrayPtr(buf_t), rffi.UINT], rffi.INT)

is_readable = llexternal("uv_is_readable", [stream_ptr], rffi.INT)
is_writable = llexternal("uv_is_writable", [stream_ptr], rffi.INT)

stream_set_blocking = llexternal("uv_stream_set_blocking", [stream_ptr, rffi.INT], rffi.INT)
is_closing = llexternal("uv_is_closing", [handle_ptr], rffi.INT)

tcp_init    = llexternal("uv_tcp_init", [loop_ptr, tcp_ptr], rffi.INT)
tcp_init_ex = llexternal("uv_tcp_init_ex", [loop_ptr, tcp_ptr, rffi.UINT], rffi.INT)
tcp_open    = llexternal("uv_tcp_open", [tcp_ptr, os_sock_t], rffi.INT)
tcp_nodelay = llexternal("uv_tcp_nodelay", [tcp_ptr, rffi.INT], rffi.INT)
tcp_keepalive = llexternal("uv_tcp_keepalive", [tcp_ptr, rffi.INT, rffi.UINT], rffi.INT)
tcp_simultaneous_accepts = llexternal("uv_tcp_simultaneous_accepts", [tcp_ptr, rffi.INT], rffi.INT)

tcp_flags = rffi.INT
TCP_IPV6ONLY = 1

tcp_bind = llexternal("uv_tcp_bind", [tcp_ptr, sockaddr_ptr, rffi.UINT], rffi.INT)
tcp_getsockname = llexternal("uv_tcp_getsockname", [tcp_ptr, sockaddr_ptr, rffi.INTP], rffi.INT)
tcp_getpeername = llexternal("uv_tcp_getpeername", [tcp_ptr, sockaddr_ptr, rffi.INTP], rffi.INT)
tcp_connect = llexternal("uv_tcp_connect", [connect_ptr, tcp_ptr, sockaddr_ptr, connect_cb], rffi.INT)

UDP_IPV6ONLY = 1
UDP_PARTIAL = 2
UDP_REUSEADDR = 4
 

udp_send_cb = rffi.CCallback([udp_send_ptr, rffi.INT], lltype.Void)
udp_recv_cb = rffi.CCallback([udp_ptr, rffi.SSIZE_T, buf_ptr, sockaddr_ptr, rffi.UINT], lltype.Void)

udp_init = llexternal("uv_udp_init", [loop_ptr, udp_ptr], rffi.INT)
udp_init_ex = llexternal("uv_udp_init_ex", [loop_ptr, udp_ptr, rffi.UINT], rffi.INT)
udp_open = llexternal("uv_udp_open", [udp_ptr, os_sock_t], rffi.INT)
udp_bind = llexternal("uv_udp_bind", [udp_ptr, sockaddr_ptr, rffi.INT], rffi.INT)

udp_getsockname = llexternal("uv_udp_getsockname", [udp_ptr, sockaddr_ptr, rffi.INTP], rffi.INT)
udp_set_membership = llexternal("uv_udp_set_membership", [udp_ptr, rffi.CCHARP, rffi.CCHARP, membership], rffi.INT)

udp_set_multicast_loop = llexternal("uv_udp_set_multicast_loop", [udp_ptr, rffi.INT], rffi.INT)
udp_set_multicast_ttl = llexternal("uv_udp_set_multicast_ttl", [udp_ptr, rffi.INT], rffi.INT)
udp_set_multicast_interface = llexternal("uv_udp_set_multicast_interface", [udp_ptr, rffi.CCHARP], rffi.INT)
udp_set_broadcast = llexternal("uv_udp_set_broadcast", [udp_ptr, rffi.INT], rffi.INT)
udp_set_ttl = llexternal("uv_udp_set_ttl", [udp_ptr, rffi.INT], rffi.INT)
udp_send = llexternal("uv_udp_send", [udp_send_ptr, udp_ptr, rffi.CArrayPtr(buf_t), rffi.UINT, sockaddr_ptr, udp_send_cb], rffi.INT)

udp_try_send = llexternal("uv_udp_try_send", [udp_ptr, rffi.CArrayPtr(buf_t), rffi.UINT, sockaddr_ptr], rffi.INT)
udp_recv_start = llexternal("uv_udp_recv_start", [udp_ptr, alloc_cb, udp_recv_cb], rffi.INT)
udp_recv_stop = llexternal("uv_udp_recv_stop", [udp_ptr], rffi.INT)
 
tty_mode_t = rffi.INT
TTY_MODE_NORMAL = 0
TTY_MODE_RAW = 1
TTY_MODE_IO = 2
 
tty_init = llexternal("uv_tty_init", [loop_ptr, tty_ptr, uv_file, rffi.INT], rffi.INT)
tty_set_mode = llexternal("uv_tty_set_mode", [tty_ptr, tty_mode_t], rffi.INT)
tty_reset_mode = llexternal("uv_tty_reset_mode", [], rffi.INT)
tty_get_winsize = llexternal("uv_tty_get_winsize", [tty_ptr, rffi.INTP, rffi.INTP], rffi.INT)

guess_handle = llexternal("uv_guess_handle", [uv_file], handle_type)
 
pipe_init = llexternal("uv_pipe_init", [loop_ptr, pipe_ptr, rffi.INT], rffi.INT)
pipe_open = llexternal("uv_pipe_open", [pipe_ptr, uv_file], rffi.INT)
pipe_bind = llexternal("uv_pipe_bind", [pipe_ptr, rffi.CCHARP], rffi.INT)
pipe_connect = llexternal("uv_pipe_connect", [connect_ptr, pipe_ptr, rffi.CCHARP, connect_cb], lltype.Void)
pipe_getsockname = llexternal("uv_pipe_getsockname", [pipe_ptr, rffi.CCHARP, rffi.SIZE_TP], rffi.INT)
pipe_getpeername = llexternal("uv_pipe_getpeername", [pipe_ptr, rffi.CCHARP, rffi.SIZE_TP], rffi.INT)

pipe_pending_instances = llexternal("uv_pipe_pending_instances", [pipe_ptr, rffi.INT], lltype.Void)
pipe_pending_count = llexternal("uv_pipe_pending_count", [pipe_ptr], rffi.INT)
pipe_pending_type = llexternal("uv_pipe_pending_type", [pipe_ptr], handle_type)

READABLE = 1
WRITABLE = 2
DISCONNECT = 4

#poll_init = llexternal("uv_poll_init", [loop_ptr, poll_ptr, rffi.INT], rffi.INT)
#poll_init_socket = llexternal("uv_poll_init_socket", [loop_ptr, poll_ptr, os_sock_t], rffi.INT)
#poll_start = llexternal("uv_poll_start", [poll_ptr, rffi.INT, poll_cb], rffi.INT)
#poll_stop = llexternal("uv_poll_stop", [poll_ptr], rffi.INT)
# 
#prepare_init = llexternal("uv_prepare_init", [loop_ptr, prepare_ptr], rffi.INT)
#prepare_start = llexternal("uv_prepare_start", [prepare_ptr, prepare_cb], rffi.INT)
#prepare_stop = llexternal("uv_prepare_stop", [prepare_ptr], rffi.INT)
# 
check_init = llexternal("uv_check_init",   [loop_ptr,  check_ptr], rffi.INT)
check_start = llexternal("uv_check_start", [check_ptr, check_cb],  rffi.INT)
check_stop = llexternal("uv_check_stop",   [check_ptr], rffi.INT)
 
idle_init = llexternal("uv_idle_init",   [loop_ptr, idle_ptr], rffi.INT)
idle_start = llexternal("uv_idle_start", [idle_ptr, idle_cb],  rffi.INT)
idle_stop = llexternal("uv_idle_stop",   [idle_ptr], rffi.INT)

#async_init = llexternal("uv_async_init", [async_ptr, async_cb], rffi.INT)
#async_send = llexternal("uv_async_send", [async_ptr], rffi.INT)
# 
timer_init = llexternal("uv_timer_init", [loop_ptr, timer_ptr], rffi.INT)
timer_start = llexternal("uv_timer_start", [timer_ptr, timer_cb, uint64_t, uint64_t], rffi.INT)
timer_stop = llexternal("uv_timer_stop", [timer_ptr], rffi.INT)
timer_again = llexternal("uv_timer_again", [timer_ptr], rffi.INT)
timer_set_repeat = llexternal("uv_timer_set_repeat", [timer_ptr, uint64_t], lltype.Void)
timer_get_repeat = llexternal("uv_timer_get_repeat", [timer_ptr], uint64_t)
 
getaddrinfo = llexternal("uv_getaddrinfo", [loop_ptr, getaddrinfo_ptr, getaddrinfo_cb, rffi.CCHARP, rffi.CCHARP, addrinfo_ptr], rffi.INT)
freeaddrinfo = llexternal("uv_freeaddrinfo", [addrinfo_ptr], lltype.Void)
getnameinfo = llexternal("uv_getnameinfo", [loop_ptr, getnameinfo_ptr, getnameinfo_cb, sockaddr_ptr, rffi.INT], rffi.INT)

IGNORE = 0x00
CREATE_PIPE = 0x01
INHERIT_FD = 0x02
INHERIT_STREAM = 0x04
READABLE_PIPE = 0x10
WRITABLE_PIPE = 0x20

#    * Set the child process' user id. The user id is supplied in the `uid` field
#    * of the options struct. This does not work on windows; setting this flag
#    * will cause uv_spawn() to fail.
PROCESS_SETUID = (1 << 0)
#    * Set the child process' group id. The user id is supplied in the `gid`
#    * field of the options struct. This does not work on windows; setting this
#    * flag will cause uv_spawn() to fail.
PROCESS_SETGID = (1 << 1)
#    * Do not wrap any arguments in quotes, or perform any other escaping, when
#    * converting the argument list into a command line string. This option is
#    * only meaningful on Windows systems. On Unix it is silently ignored.
PROCESS_WINDOWS_VERBATIM_ARGUMENTS = (1 << 2)
#    * Spawn the child process in a detached state - this will make it a process
#    * group leader, and will effectively enable the child to keep running after
#    * the parent exits.  Note that the child process will still keep the
#    * parent's event loop alive unless the parent process calls uv_unref() on
#    * the child's process handle.
PROCESS_DETACHED = (1 << 3)
#    * Hide the subprocess console window that would normally be created. This
#    * option is only meaningful on Windows systems. On Unix it is silently
#    * ignored.
PROCESS_WINDOWS_HIDE = (1 << 4)


spawn = llexternal("uv_spawn", [loop_ptr, process_ptr, process_options_ptr], rffi.INT)
process_kill = llexternal("uv_process_kill", [process_ptr, rffi.INT], rffi.INT)
kill = llexternal("uv_kill", [rffi.INT, rffi.INT], rffi.INT)

queue_work = llexternal("uv_queue_work", [loop_ptr, work_ptr, work_cb, after_work_cb], rffi.INT)
#cancel = llexternal("uv_cancel", [req_ptr], rffi.INT)
# 
# struct uv_cpu_info_s {
#   char* model;
#   int speed;
#   struct uv_cpu_times_s {
#     uint64_t user;
#     uint64_t nice;
#     uint64_t sys;
#     uint64_t idle;
#     uint64_t irq;
#   } cpu_times;
# };
# 
# struct uv_interface_address_s {
#   char* name;
#   char phys_addr[6];
#   int is_internal;
#   union {
#     struct sockaddr_in address4;
#     struct sockaddr_in6 address6;
#   } address;
#   union {
#     struct sockaddr_in netmask4;
#     struct sockaddr_in6 netmask6;
#   } netmask;
# };
# 
# struct uv_passwd_s {
#   char* username;
#   long uid;
#   long gid;
#   char* shell;
#   char* homedir;
# };
# 

(DIRENT_UNKNOWN,
DIRENT_FILE,
DIRENT_DIR,
DIRENT_LINK,
DIRENT_FIFO,
DIRENT_SOCKET,
DIRENT_CHAR,
DIRENT_BLOCK) = range(8)
dirent2name = {
    DIRENT_UNKNOWN:u"unknown",
    DIRENT_FILE:u"file",
    DIRENT_DIR:u"dir",
    DIRENT_LINK:u"link",
    DIRENT_FIFO:u"fifo",
    DIRENT_SOCKET:u"socket",
    DIRENT_CHAR:u"char",
    DIRENT_BLOCK:u"block"
}

#setup_args = llexternal("uv_setup_args", [rffi.INT, rffi.CCHARPP], rffi.CCHARPP)
#get_process_title = llexternal("uv_get_process_title", [rffi.CCHARP, rffi.SIZE_T], rffi.INT)
#set_process_title = llexternal("uv_set_process_title", [rffi.CCHARP], rffi.INT)
#resident_set_memory = llexternal("uv_resident_set_memory", [rffi.SIZE_TP], rffi.INT)
#uptime = llexternal("uv_uptime", [rffi.CArrayPtr(rffi.DOUBLE)], rffi.INT)
 
timeval_t = rffi.CStruct("uv_timeval_t",
    ("tv_sec",  rffi.LONG),
    ("tv_usec", rffi.LONG))
 

rusage_t = rffi.CStruct("uv_rusage_t",
    ("ru_utime",     timeval_t), # user CPU time used
    ("ru_stime",     timeval_t), # system CPU time used
    ("ru_maxrss",    uint64_t), # maximum resident set size
    ("ru_ixrss",     uint64_t), # integral shared memory size
    ("ru_idrss",     uint64_t), # integral unshared data size
    ("ru_isrss",     uint64_t), # integral unshared stack size
    ("ru_minflt",    uint64_t), # page reclaims (soft page faults)
    ("ru_majflt",    uint64_t), # page faults (hard page faults)
    ("ru_nswap",     uint64_t), # swaps
    ("ru_inblock",   uint64_t), # block input operations
    ("ru_oublock",   uint64_t), # block output operations
    ("ru_msgsnd",    uint64_t), # IPC messages sent
    ("ru_msgrcv",    uint64_t), # IPC messages received
    ("ru_nsignals",  uint64_t), # signals received
    ("ru_nvcsw",     uint64_t), # voluntary context switches
    ("ru_nivcsw",    uint64_t)) # involuntary context switches
rusage_ptr = lltype.Ptr(rusage_t)

#getrusage = llexternal("uv_getrusage", [rusage_ptr], rffi.INT)
# 
#os_homedir = llexternal("uv_os_homedir", [rffi.CCHARP, rffi.SIZE_TP], rffi.INT)
#os_tmpdir = llexternal("uv_os_tmpdir", [rffi.CCHARP, rrfi.SIZE_TP], rffi.INT)
#os_get_passwd = llexternal("uv_os_get_passwd", [passwd_ptr], rffi.INT)
#os_free_passwd = llexternal("uv_os_free_passwd", [passwd_ptr], lltype.Void)
# 
#cpu_info = llexternal("uv_cpu_info", [cpu_info_pptr, rffi.INTP], rffi.INT)
#free_cpu_info = llexternal("uv_free_cpu_info", [cpu_info_ptr, rffi.INT], lltype.Void)
# 
#interface_addresses = llexternal("uv_interface_addresses", [interface_address_pptr, rffi.INTP], rffi.INT)
#free_interface_addresses = llexternal("uv_free_interface_addresses", [interface_address_ptr, rffi.INT], lltype.Void)

fs_type = rffi.INT
(
UV_FS_UNKNOWN,
UV_FS_CUSTOM,
UV_FS_OPEN,
UV_FS_CLOSE,
UV_FS_READ,
UV_FS_WRITE,
UV_FS_SENDFILE,
UV_FS_STAT,
UV_FS_LSTAT,
UV_FS_FSTAT,
UV_FS_FTRUNCATE,
UV_FS_UTIME,
UV_FS_FUTIME,
UV_FS_ACCESS,
UV_FS_CHMOD,
UV_FS_FCHMOD,
UV_FS_FSYNC,
UV_FS_FDATASYNC,
UV_FS_UNLINK,
UV_FS_RMDIR,
UV_FS_MKDIR,
UV_FS_MKDTEMP,
UV_FS_RENAME,
UV_FS_SCANDIR,
UV_FS_LINK,
UV_FS_SYMLINK,
UV_FS_READLINK,
UV_FS_CHOWN,
UV_FS_FCHOWN,
UV_FS_REALPATH
) = range(30)

fs_req_cleanup = llexternal("uv_fs_req_cleanup", [fs_ptr], lltype.Void)
fs_close = llexternal("uv_fs_close", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
fs_open = llexternal("uv_fs_open", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, rffi.INT, fs_cb], rffi.INT)
fs_read = llexternal("uv_fs_read", [loop_ptr, fs_ptr, uv_file, rffi.CArrayPtr(buf_t), rffi.UINT, int64_t, fs_cb], rffi.INT)
fs_unlink = llexternal("uv_fs_unlink", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
fs_write = llexternal("uv_fs_write", [loop_ptr, fs_ptr, uv_file, rffi.CArrayPtr(buf_t), rffi.UINT, int64_t, fs_cb], rffi.INT)
fs_mkdir = llexternal("uv_fs_mkdir", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
fs_mkdtemp = llexternal("uv_fs_mkdtemp", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
fs_rmdir = llexternal("uv_fs_rmdir", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
fs_scandir = llexternal("uv_fs_scandir", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
fs_scandir_next = llexternal("uv_fs_scandir_next", [fs_ptr, dirent_ptr], rffi.INT)
fs_stat = llexternal("uv_fs_stat", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
fs_fstat = llexternal("uv_fs_fstat", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
fs_rename = llexternal("uv_fs_rename", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.CCHARP, fs_cb], rffi.INT)
fs_fsync = llexternal("uv_fs_fsync", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
fs_fdatasync = llexternal("uv_fs_fdatasync", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
fs_ftruncate = llexternal("uv_fs_ftruncate", [loop_ptr, fs_ptr, uv_file, int64_t, fs_cb], rffi.INT)
fs_sendfile = llexternal("uv_fs_sendfile", [loop_ptr, fs_ptr, uv_file, uv_file, int64_t, rffi.SIZE_T, fs_cb], rffi.INT)
fs_access = llexternal("uv_fs_access", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
fs_chmod = llexternal("uv_fs_chmod", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
fs_utime = llexternal("uv_fs_utime", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.DOUBLE, rffi.DOUBLE, fs_cb], rffi.INT)
fs_futime = llexternal("uv_fs_futime", [loop_ptr, fs_ptr, uv_file, rffi.DOUBLE, rffi.DOUBLE, fs_cb], rffi.INT)
fs_lstat = llexternal("uv_fs_lstat", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
fs_link = llexternal("uv_fs_link", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.CCHARP, fs_cb], rffi.INT)
 
FS_SYMLINK_DIR = 0x0001
FS_SYMLINK_JUNCTION = 0x0002
 
fs_symlink = llexternal("uv_fs_symlink", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
fs_readlink = llexternal("uv_fs_readlink", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
fs_realpath = llexternal("uv_fs_realpath", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
fs_fchmod = llexternal("uv_fs_fchmod", [loop_ptr, fs_ptr, uv_file, rffi.INT, fs_cb], rffi.INT)
fs_chown = llexternal("uv_fs_chown", [loop_ptr, fs_ptr, rffi.CCHARP, uid_t, gid_t, fs_cb], rffi.INT)
fs_fchown = llexternal("uv_fs_fchown", [loop_ptr, fs_ptr, uv_file, uid_t, gid_t, fs_cb], rffi.INT)

fs_event = rffi.INT
RENAME = 1
CHANGE = 2
# 
#fs_poll_init = llexternal("uv_fs_poll_init", [loop_ptr, fs_poll_ptr], rffi.INT)
#fs_poll_start = llexternal("uv_fs_poll_start", [loop_ptr, fs_poll_cb, rffi.CCHARP, rffi.UINT], rffi.INT)
#fs_poll_stop = llexternal("uv_fs_poll_stop", [fs_poll_ptr], rffi.INT)
#fs_poll_getpath = llexternal("uv_fs_poll_getpath", [fs_poll_ptr, rffi.CCHARP, rffi.SIZE_TP], rffi.INT)
# 
#signal_init = llexternal("uv_signal_init", [loop_ptr, signal_ptr], rffi.INT)
#signal_start = llexternal("uv_signal_start", [signal_ptr, signal_cb, rffi.INT], rffi.INT)
#signal_stop = llexternal("uv_signal_stop", [signal_ptr], rffi.INT)
# 
#loadavg = llexternal("uv_loadavg", [rffi.CFixedArray(rffi.DOUBLE, 3)], lltype.Void)
# 
fs_event_flags = rffi.INT
FS_EVENT_WATCH_ENTRY = 1
FS_EVENT_STAT = 2
FS_EVENT_RECURSIVE = 4
 
fs_event_init = llexternal("uv_fs_event_init", [loop_ptr, fs_event_ptr], rffi.INT)
fs_event_start = llexternal("uv_fs_event_start", [fs_event_ptr, fs_event_cb, rffi.CCHARP, rffi.UINT], rffi.INT)
fs_event_stop = llexternal("uv_fs_event_stop", [fs_event_ptr], rffi.INT)
#fs_event_getpath = llexternal("uv_fs_event_getpath", [fs_event_ptr, rffi.CCHARP, rffi.SIZE_TP], rffi.INT)

sockaddr_in_ptr = rffi.VOIDP
sockaddr_in6_ptr = rffi.VOIDP

ip4_addr = llexternal("uv_ip4_addr", [rffi.CCHARP, rffi.INT, sockaddr_in_ptr], rffi.INT)
ip6_addr = llexternal("uv_ip6_addr", [rffi.CCHARP, rffi.INT, sockaddr_in6_ptr], rffi.INT)
 
ip4_name = llexternal("uv_ip4_name", [sockaddr_in_ptr, rffi.CCHARP, rffi.SIZE_T], rffi.INT)
ip6_name = llexternal("uv_ip6_name", [sockaddr_in6_ptr, rffi.CCHARP, rffi.SIZE_T], rffi.INT)
 
inet_ntop = llexternal("uv_inet_ntop", [rffi.INT, rffi.VOIDP, rffi.CCHARP, rffi.SIZE_T], rffi.INT)
inet_pton = llexternal("uv_inet_pton", [rffi.INT, rffi.CCHARP, rffi.VOIDP], rffi.INT)
# 
#exepath = llexternal("uv_exepath", [rffi.CCHARP, rffi.SIZE_TP], rffi.INT)
# 
#cwd = llexternal("uv_cwd", [rffi.CCHARP, rffi.SIZE_TP], rffi.INT)
# 
#chdir = llexternal("uv_chdir", [rffi.CCHARP], rffi.INT)
# 
#get_free_memory = llexternal("uv_get_free_memory", [], uint64_t)
#get_total_memory = llexternal("uv_get_total_memory", [], uint64_t)
# 
#hrtime = llexternal("uv_hrtime", [], uint64_t)
# 
#disable_stdio_inheritance = llexternal("uv_disable_stdio_inheritance", [], lltype.Void)
# 
#dlopen = llexternal("uv_dlopen", [rffi.CCHARP, lib_ptr], rffi.INT)
#dlclose = llexternal("uv_dlclose", [lib_ptr], lltype.Void)
#dlsym = llexternal("uv_dlsym", [lib_ptr, rffi.CCHARP, rffi.VOIDPP], rffi.INT)
#dlerror = llexternal("uv_dlerror", [lib_ptr], rffi.CCHARP)
# 
#mutex_init = llexternal("uv_mutex_init", [mutex_ptr], rffi.INT)
#mutex_destroy = llexternal("uv_mutex_destroy", [mutex_ptr], lltype.Void)
#mutex_lock = llexternal("uv_mutex_lock", [mutex_ptr], lltype.Void)
#mutex_trylock = llexternal("uv_mutex_trylock", [mutex_ptr], rffi.INT)
#mutex_unlock = llexternal("uv_mutex_unlock", [mutex_ptr], lltype.Void)
# 
#rwlock_init = llexternal("uv_rwlock_init", [rwlock_ptr], rffi.INT)
#rwlock_destroy = llexternal("uv_rwlock_destroy", [rwlock_ptr], lltype.Void)
#rwlock_rdlock = llexternal("uv_rwlock_rdlock", [rwlock_ptr], lltype.Void)
#rwlock_tryrdlock = llexternal("uv_rwlock_tryrdlock", [rwlock_ptr], rffi.INT)
#rwlock_rdunlock = llexternal("uv_rwlock_rdunlock", [rwlock_ptr], lltype.Void)
#rwlock_wrlock = llexternal("uv_rwlock_wrlock", [rwlock_ptr], lltype.Void)
#rwlock_trywrlock = llexternal("uv_rwlock_trywrlock", [rwlock_ptr], rffi.INT)
#rwlock_wrunlock = llexternal("uv_rwlock_wrunlock", [rwlock_ptr], lltype.Void)
# 
#sem_init = llexternal("uv_sem_init", [sem_ptr, rffi.UINT], rffi.INT)
#sem_destroy = llexternal("uv_sem_destroy", [sem_ptr], lltype.Void)
#sem_post = llexternal("uv_sem_post", [sem_ptr], lltype.Void)
#sem_wait = llexternal("uv_sem_wait", [sem_ptr], lltype.Void)
#sem_trywait = llexternal("uv_sem_trywait", [sem_ptr], rffi.INT)
# 
#cond_init = llexternal("uv_cond_init", [cond_ptr], rffi.INT)
#cond_destroy = llexternal("uv_cond_destroy", [cond_ptr], lltype.Void)
#cond_signal = llexternal("uv_cond_signal", [cond_ptr], lltype.Void)
#cond_broadcast = llexternal("uv_cond_broadcast", [cond_ptr], lltype.Void)
# 
#barrier_init = llexternal("uv_barrier_init", [barrier_ptr, rffi.UINT], rffi.INT)
#barrier_destroy = llexternal("uv_barrier_destroy", [barrier_ptr], lltype.Void)
#barrier_wait = llexternal("uv_barrier_wait", [barrier_ptr], rffi.INT)
# 
#cond_wait = llexternal("uv_cond_wait", [cond_ptr, mutex_ptr], lltype.Void)
#cond_timedwait = llexternal("uv_cond_timedwait", [cond_ptr, mutex_ptr, uint64_t], rffi.INT)
# 
SomeCallback = rffi.CCallback([], lltype.Void)
#once = llexternal("uv_once", [once_ptr, SomeCallback], lltype.Void)
# 
#key_create = llexternal("uv_key_create", [key_ptr], rffi.INT)
#key_delete = llexternal("uv_key_delete", [key_ptr], lltype.Void)
#key_get = llexternal("uv_key_get", [key_ptr], rffi.VOIDP)
#key_set = llexternal("uv_key_set", [key_ptr, rffi.VOIDP], lltype.Void)

# thread_cb = rffi.CCallback([rffi.VOIDP], lltype.Void)
# thread_create = llexternal("uv_thread_create", [thread_ptr, thread_cb, rffi.VOIDP], rffi.INT)
# thread_self = llexternal("uv_thread_self", [], thread_t)
# thread_join = llexternal("uv_thread_join", [thread_ptr], rffi.INT)
# thread_equal = llexternal("uv_thread_equal", [thread_ptr, thread_ptr], rffi.INT)


STDIO_STREAM_HELPER_C = '''
#include <uv.h>

RPY_EXTERN
void
monte_helper_set_stdio_stream(uv_stdio_container_t *stdio,
                              uv_stream_t *stream)
{
    stdio->data.stream = stream;
}

RPY_EXTERN
void
monte_helper_set_stdio_fd(uv_stdio_container_t *stdio,
                              int fd)
{
    stdio->data.fd = fd;
}
'''
stdio_stream_helper = ExternalCompilationInfo(
    includes=['uv.h'],
    separate_module_sources=[STDIO_STREAM_HELPER_C])

set_stdio_stream = rffi.llexternal("monte_helper_set_stdio_stream",
    [stdio_container_ptr, stream_ptr],
    lltype.Void,
    compilation_info=stdio_stream_helper)

set_stdio_fd = rffi.llexternal("monte_helper_set_stdio_fd",
    [stdio_container_ptr, rffi.INT],
    lltype.Void,
    compilation_info=stdio_stream_helper)
