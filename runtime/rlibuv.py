from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.rlib.objectmodel import always_inline, specialize
import os, sys

# recurring pattern, as we do not know the sizes of structures.
@specialize.call_location()
def malloc_bytes(ptr_type, size):
    return rffi.cast(ptr_type,
        lltype.malloc(rffi.CCHARP.TO, size, flavor='raw'))

@specialize.call_location()
def free(ptr):
    lltype.free(ptr, flavor='raw')

libuv_dir = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../libuv"))
def cd(x):
    return os.path.join(libuv_dir, x)

if sys.platform == "win32":
    path_to_libuv_library = cd("libuv.lib")
else:
    path_to_libuv_library = cd("out/Release/libuv.a")
    if not os.path.exists(path_to_libuv_library):
        path_to_libuv_library = cd("out/Release/libuv.a")
assert os.path.exists(path_to_libuv_library), "cannot find libuv, check it is in libuv/ path."

# This thing seemed to not appear in official includes..
assert os.path.exists(
    cd("include/stdint-msvc2008.h")
), "Download https://github.com/libuv/libuv/blob/v1.x/include/stdint-msvc2008.h into libuv/include/, please."

eci = ExternalCompilationInfo(
    include_dirs = [
        cd("include")
    ],
    includes = [
        cd("include/uv.h")
    ],
    # library_dirs = [
    #    "libuv/out/Release"
    # ],
    link_files = [
        path_to_libuv_library
    ]
)

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

# Handle types
loop_ptr = rffi.COpaquePtr("uv_loop_t")
handle_ptr = rffi.COpaquePtr("uv_handle_t")
stream_ptr = rffi.COpaquePtr("uv_stream_t")
tcp_ptr = rffi.COpaquePtr("uv_tcp_t")
udp_ptr = rffi.COpaquePtr("uv_udp_t")
pipe_ptr = rffi.COpaquePtr("uv_pipe_t")
tty_ptr = rffi.COpaquePtr("uv_tty_t")
poll_ptr = rffi.COpaquePtr("uv_poll_t")
timer_ptr = rffi.COpaquePtr("uv_timer_t")
prepare_ptr = rffi.COpaquePtr("uv_prepare_t")
check_ptr = rffi.COpaquePtr("uv_check_t")
idle_ptr = rffi.COpaquePtr("uv_idle_t")
async_ptr = rffi.COpaquePtr("uv_async_t")
process_ptr = rffi.COpaquePtr("uv_process_t")
fs_event_ptr = rffi.COpaquePtr("uv_fs_event_t")
fs_poll_ptr = rffi.COpaquePtr("uv_fs_poll_t")
signal_ptr = rffi.COpaquePtr("uv_signal_t")

# Request types
req_ptr = rffi.COpaquePtr("uv_req_t")
getaddrinfo_ptr = rffi.COpaquePtr("uv_getaddrinfo_t")
getnameinfo_ptr = rffi.COpaquePtr("uv_getnameinfo_t")
shutdown_ptr = rffi.COpaquePtr("uv_thutdown_s")
write_ptr = rffi.COpaquePtr("uv_write_t")
connect_ptr = rffi.COpaquePtr("uv_connect_t")
udp_send_ptr = rffi.COpaquePtr("uv_udp_send_s")
fs_ptr = rffi.COpaquePtr("uv_fs_t")
work_ptr = rffi.COpaquePtr("uv_work_t")

# None of the above
cpu_info_ptr = rffi.COpaquePtr("uv_cpu_info_s")
interface_address_ptr = rffi.COpaquePtr("uv_interface_address_s")
dirent_ptr = rffi.COpaquePtr("uv_dirent_s")
passwd_ptr = rffi.COpaquePtr("uv_passwd_s")

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
    buf_t = lltype.Struct("uv_buf_t",
        ("base", rffi.CCHARP),
        ("size", rffi.SIZE_T))
    os_sock_t = rffi.INT
else:
    buf_t = lltype.Struct("uv_buf_t",
        ("size", rffi.SIZE_T), # or ULONG
        ("base", rffi.CCHARP))
    os_sock_t = rffi.VOIDP

uv_file = rffi.INT

sockaddr_ptr = rffi.VOIDP # hmm? TODO: find this thing up in rpython

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
exit_cb        = rffi.CCallback([process_ptr,    int64_t, rffi.INT],      lltype.Void)
walk_cb        = rffi.CCallback([handle_ptr,     rffi.VOIDP],             lltype.Void)
fs_cb          = rffi.CCallback([fs_ptr],                                 lltype.Void)
work_cb        = rffi.CCallback([work_ptr],                               lltype.Void)
after_work_cb  = rffi.CCallback([work_ptr,       rffi.INT],               lltype.Void)

addrinfo_ptr = rffi.VOIDP # struct addrinfo*
getaddrinfo_cb = rffi.CCallback([getaddrinfo_ptr, rffi.INT, addrinfo_ptr], lltype.Void)
getnameinfo_cb = rffi.CCallback([getnameinfo_ptr, rffi.INT, rffi.CCHARP, rffi.CCHARP], lltype.Void)

timespec_t = rffi.CStruct("uv_timespec_t",
    ("tv_sec",  rffi.LONG),
    ("tv_nsec", rffi.LONG))
# typedef struct {
#   long tv_sec;
#   long tv_nsec;
# } uv_timespec_t;

stat_t = rffi.CStruct("uv_stat_t",
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
    ("st_birthtim", timespec_t))

fs_event_cb = rffi.CCallback([fs_event_ptr, rffi.CCHARP, rffi.INT, rffi.INT], lltype.Void)
fs_poll_cb  = rffi.CCallback([fs_poll_ptr, rffi.INT, lltype.Ptr(stat_t), lltype.Ptr(stat_t)], lltype.Void)
signal_cb   = rffi.CCallback([signal_ptr, rffi.INT], lltype.Void)

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

# UV_EXTERN int uv_fileno(const uv_handle_t* handle, uv_os_fd_t* fd);
 
def buf_init(uv_buf, base, length):
    uv_buf
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
# 
#getaddrinfo = llexternal("uv_getaddrinfo", [loop_ptr, uv_getaddrinfo_ptr, getaddrinfo_cb, rffi.CCHARP, rffi.CCHARP, addrinfo_ptr], rffi.INT)
#freeaddrinfo = llexternal("uv_freeaddrinfo", [addrinfo_ptr], lltype.Void)
# 
#getnameinfo = llexternal("uv_getnameinfo", [loop_ptr, uv_getnameinfo_ptr, getnameinfo_cb, sockaddr_ptr, rffi.INT], rffi.INT)

stdio_flags = rffi.INT
IGNORE = 0x00
CREATE_PIPE = 0x01
INHERIT_FD = 0x02
INHERIT_STREAM = 0x04
READABLE_PIPE = 0x10
WRITABLE_PIPE = 0x20

stdio_container = rffi.CStruct("uv_stdio_container_t",
    ("flags", stdio_flags),
    ("data", rffi.VOIDP)) # stream_ptr, (int fd)

# typedef struct uv_process_options_s {
#   uv_exit_cb exit_cb; /* Called after the process exits. */
#   const char* file;   /* Path to program to execute. */
#   /*
#    * Command line arguments. args[0] should be the path to the program. On
#    * Windows this uses CreateProcess which concatenates the arguments into a
#    * string this can cause some strange errors. See the note at
#    * windows_verbatim_arguments.
#    */
#   char** args;
#   /*
#    * This will be set as the environ variable in the subprocess. If this is
#    * NULL then the parents environ will be used.
#    */
#   char** env;
#   /*
#    * If non-null this represents a directory the subprocess should execute
#    * in. Stands for current working directory.
#    */
#   const char* cwd;
#   /*
#    * Various flags that control how uv_spawn() behaves. See the definition of
#    * `enum uv_process_flags` below.
#    */
#   unsigned int flags;
#   /*
#    * The `stdio` field points to an array of uv_stdio_container_t structs that
#    * describe the file descriptors that will be made available to the child
#    * process. The convention is that stdio[0] points to stdin, fd 1 is used for
#    * stdout, and fd 2 is stderr.
#    *
#    * Note that on windows file descriptors greater than 2 are available to the
#    * child process only if the child processes uses the MSVCRT runtime.
#    */
#   int stdio_count;
#   uv_stdio_container_t* stdio;
#   /*
#    * Libuv can change the child process' user/group id. This happens only when
#    * the appropriate bits are set in the flags fields. This is not supported on
#    * windows; uv_spawn() will fail and set the error to UV_ENOTSUP.
#    */
#   uv_uid_t uid;
#   uv_gid_t gid;
# } uv_process_options_t;
# 
# /*
#  * These are the flags that can be used for the uv_process_options.flags field.
#  */
# enum uv_process_flags {
#   /*
#    * Set the child process' user id. The user id is supplied in the `uid` field
#    * of the options struct. This does not work on windows; setting this flag
#    * will cause uv_spawn() to fail.
#    */
#   UV_PROCESS_SETUID = (1 << 0),
#   /*
#    * Set the child process' group id. The user id is supplied in the `gid`
#    * field of the options struct. This does not work on windows; setting this
#    * flag will cause uv_spawn() to fail.
#    */
#   UV_PROCESS_SETGID = (1 << 1),
#   /*
#    * Do not wrap any arguments in quotes, or perform any other escaping, when
#    * converting the argument list into a command line string. This option is
#    * only meaningful on Windows systems. On Unix it is silently ignored.
#    */
#   UV_PROCESS_WINDOWS_VERBATIM_ARGUMENTS = (1 << 2),
#   /*
#    * Spawn the child process in a detached state - this will make it a process
#    * group leader, and will effectively enable the child to keep running after
#    * the parent exits.  Note that the child process will still keep the
#    * parent's event loop alive unless the parent process calls uv_unref() on
#    * the child's process handle.
#    */
#   UV_PROCESS_DETACHED = (1 << 3),
#   /*
#    * Hide the subprocess console window that would normally be created. This
#    * option is only meaningful on Windows systems. On Unix it is silently
#    * ignored.
#    */
#   UV_PROCESS_WINDOWS_HIDE = (1 << 4)
# };
# 
# /*
#  * uv_process_t is a subclass of uv_handle_t.
#  */
# struct uv_process_s {
#   UV_HANDLE_FIELDS
#   uv_exit_cb exit_cb;
#   int pid;
#   UV_PROCESS_PRIVATE_FIELDS
# };
# 
#spawn = llexternal("uv_spawn", [loop_ptr, process_ptr, process_options_ptr], rffi.INT)
#process_kill = llexternal("uv_process_kill", [process_ptr, rffi.INT], rffi.INT)
#kill = llexternal("uv_kill", [rffi.INT, rffi.INT], rffi.INT)
#queue_work = llexternal("uv_queue_work", [loop_ptr, work_ptr, work_cb, after_work_cb], rffi.INT)
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
# typedef enum {
#   UV_DIRENT_UNKNOWN,
#   UV_DIRENT_FILE,
#   UV_DIRENT_DIR,
#   UV_DIRENT_LINK,
#   UV_DIRENT_FIFO,
#   UV_DIRENT_SOCKET,
#   UV_DIRENT_CHAR,
#   UV_DIRENT_BLOCK
# } uv_dirent_type_t;
# 
# struct uv_dirent_s {
#   const char* name;
#   uv_dirent_type_t type;
# };
# 
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

#fs_req_cleanup = llexternal("uv_fs_req_cleanup", [fs_ptr], lltype.Void)
#fs_close = llexternal("uv_fs_close", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
#fs_open = llexternal("uv_fs_open", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, rffi.INT, fs_cb], rffi.INT)
#fs_read = llexternal("uv_fs_read", [loop_ptr, fs_ptr, uv_file, rffi.CArray(buf_t), rffi.UINT, int64_t, fs_cb], rffi.INT)
#fs_unlink = llexternal("uv_fs_unlink", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
#fs_write = llexternal("uv_fs_write", [loop_ptr, fs_ptr, uv_file, rffi.CArray(buf_t), rffi.UINT, int64_t, fs_cb], rffi.INT)
#fs_mkdir = llexternal("uv_fs_mkdir", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
#fs_mkdtemp = llexternal("uv_fs_mkdtemp", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
#fs_rmdir = llexternal("uv_fs_rmdir", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
#fs_scandir = llexternal("uv_fs_scandir", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
#fs_scandir_next = llexternal("uv_fs_scandir_next", [fs_ptr, dirent_ptr], rffi.INT)
#fs_stat = llexternal("uv_fs_stat", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
#fs_fstat = llexternal("uv_fs_fstat", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
#fs_rename = llexternal("uv_fs_rename", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.CCHARP, fs_cb], rffi.INT)
#fs_fsync = llexternal("uv_fs_fsync", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
#fs_fdatasync = llexternal("uv_fs_fdatasync", [loop_ptr, fs_ptr, uv_file, fs_cb], rffi.INT)
#fs_ftruncate = llexternal("uv_fs_ftruncate", [loop_ptr, fs_ptr, uv_file, int64_t, fs_cb], rffi.INT)
#fs_sendfile = llexternal("uv_fs_sendfile", [loop_ptr, fs_ptr, uv_file, uv_file, int64_t, rffi.SIZE_T, fs_cb], rffi.INT)
#fs_access = llexternal("uv_fs_access", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
#fs_chmod = llexternal("uv_fs_chmod", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
#fs_utime = llexternal("uv_fs_utime", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.DOUBLE, rffi.DOUBLE, fs_cb], rffi.INT)
#fs_futime = llexternal("uv_fs_futime", [loop_ptr, fs_ptr, uv_file, rffi.DOUBLE, rffi.DOUBLE, fs_cb], rffi.INT)
#fs_lstat = llexternal("uv_fs_lstat", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
#fs_link = llexternal("uv_fs_link", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.CCHARP, fs_cb], rffi.INT)
# 
#FS_SYMLINK_DIR = 0x0001
#FS_SYMLINK_JUNCTION 0x0002
 
#fs_symlink = llexternal("uv_fs_symlink", [loop_ptr, fs_ptr, rffi.CCHARP, rffi.CCHARP, rffi.INT, fs_cb], rffi.INT)
#fs_readlink = llexternal("uv_fs_readlink", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
#fs_realpath = llexternal("uv_fs_realpath", [loop_ptr, fs_ptr, rffi.CCHARP, fs_cb], rffi.INT)
#fs_fchmod = llexternal("uv_fs_fchmod", [loop_ptr, fs_ptr, uv_file, rffi.INT, fs_cb], rffi.INT)
#fs_chown = llexternal("uv_fs_chown", [loop_ptr, fs_ptr, rffi.CCHARP, uid_t, gid_t, fs_cb], rffi.INT)
#fs_fchown = llexternal("uv_fs_fchown", [loop_ptr, fs_ptr, uv_file, uid_t, gid_t, fs_cb], rffi.INT)

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
 
#fs_event_init = llexternal("uv_fs_event_init", [loop_ptr, fs_event_ptr], rffi.INT)
#fs_event_start = llexternal("uv_fs_event_start", [fs_event_ptr, fs_event_cb, rffi.CCHARP, rffi.UINT], rffi.INT)
#fs_event_stop = llexternal("uv_fs_event_stop", [fs_event_ptr], rffi.INT)
#fs_event_getpath = llexternal("uv_fs_event_getpath", [fs_event_ptr, rffi.CCHARP, rffi.SIZE_TP], rffi.INT)
#ip4_addr = llexternal("uv_ip4_addr", [rffi.CCHARP, rffi.INT, sockaddr_in_ptr], rffi.INT)
#ip6_addr = llexternal("uv_ip6_addr", [rffi.CCHARP, rffi.INT, sockaddr_in6_ptr], rffi.INT)
# 
#ip4_name = llexternal("uv_ip4_name", [sockaddr_in_ptr, rffi.CCHARP, rffi.SIZE_T], rffi.INT)
#ip6_name = llexternal("uv_ip6_name", [sockaddr_in6_ptr, rffi.CCHARP, rffi.SIZE_T], rffi.INT)
# 
#inet_ntop = llexternal("uv_inet_ntop", [rffi.INT, rffi.VOIDP, rffi.CCHARP, rffi.SIZE_T], rffi.INT)
#inet_pton = llexternal("uv_inet_pton", [rffi.INT, rffi.CCHARP, rffi.VOIDP], rffi.INT)
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
