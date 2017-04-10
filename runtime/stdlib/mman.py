from space import *
#from rpython.rlib.objectmodel import always_inline, specialize
from rpython.rlib import rgc
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
#from rpython.rtyper.tool import rffi_platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo
import sys

# The ideas in this module originate from this blogpost:
#
#   http://nullprogram.com/blog/2015/03/19/
#
#
# I may not need these right yet, but it can be motivating to see
# the assembled code to run.

MMAN_ASMBUF_C_UNIX = '''
#include <unistd.h>
#include <sys/mman.h>
#include <stdlib.h>
#include <stddef.h>

size_t asmbuf_get_pagesize()
{
    return (size_t)sysconf(_SC_PAGESIZE);
}

void* asmbuf_create(size_t size)
{
    int prot = PROT_READ | PROT_WRITE;
    int flags = MAP_ANONYMOUS | MAP_PRIVATE;
    return mmap(NULL, size, prot, flags, -1, 0);
}

void asmbuf_finalize(void* buf, size_t size)
{
    mprotect(buf, size, PROT_READ | PROT_EXEC);
}

void asmbuf_free(void* buf, size_t size)
{
    munmap(buf, size);
}
'''

MMAN_ASMBUF_C_WIN32 = '''
#include <Windows.h>
#include <stdlib.h>
#include <stddef.h>

size_t asmbuf_get_pagesize()
{
    SYSTEM_INFO systemInfo;
    GetNativeSystemInfo (&systemInfo);
    return (size_t) systemInfo.dwPageSize;
}

void* asmbuf_create(size_t size)
{
    DWORD type = MEM_RESERVE | MEM_COMMIT;
    return VirtualAlloc(NULL, size, type, PAGE_READWRITE);
}

void asmbuf_finalize(void* buf, size_t size)
{
    DWORD old;
    VirtualProtect(buf, size, PAGE_EXECUTE_READ, &old);
}

void asmbuf_free(void* buf, size_t size)
{
    (void)(size);
    VirtualFree(buf, 0, MEM_RELEASE);
}
'''

if sys.platform == "win32":
    MMAN_ASMBUF_C = MMAN_ASMBUF_C_WIN32
else:
    MMAN_ASMBUF_C = MMAN_ASMBUF_C_UNIX

asmbuf_eci = ExternalCompilationInfo(
    separate_module_sources=[MMAN_ASMBUF_C],
    post_include_bits = [
        'RPY_EXTERN size_t asmbuf_get_pagesize();\n'
        'RPY_EXTERN void* asmbuf_create(size_t);\n'
        'RPY_EXTERN void asmbuf_finalize(void*, size_t);\n'
        'RPY_EXTERN void asmbuf_free(void*, size_t);\n'
    ])

asmbuf_get_pagesize = rffi.llexternal("asmbuf_get_pagesize",
    [], rffi.SIZE_T,
    compilation_info=asmbuf_eci)

asmbuf_create = rffi.llexternal("asmbuf_create",
    [rffi.SIZE_T], rffi.VOIDP,
    compilation_info=asmbuf_eci)

asmbuf_finalize = rffi.llexternal("asmbuf_finalize",
    [rffi.VOIDP, rffi.SIZE_T], lltype.Void,
    compilation_info=asmbuf_eci)

asmbuf_free = rffi.llexternal("asmbuf_free",
    [rffi.VOIDP, rffi.SIZE_T], lltype.Void,
    compilation_info=asmbuf_eci)

class Asmbuf(Uint8Data):
    pass

@Asmbuf.instantiator2(signature(Integer))
def Asmbuf_init(size):
    size = align(size.value, rffi.r_long(asmbuf_get_pagesize()))
    data = asmbuf_create(size)
    uint8data = rffi.cast(rffi.UCHARP, data)
    return Asmbuf(uint8data, size)

@Asmbuf.method(u"finalize", signature(Asmbuf))
def Asmbuf_finalize(self):
    asmbuf_finalize(self.uint8data, self.length)
    return null

@Asmbuf.method(u"free", signature(Asmbuf))
def Asmbuf_free(self):
    asmbuf_free(self.uint8data, self.length)
    return null

# Yeah. This is in the FFI too.
def align(x, a):
    return x + (a - x % a) % a

@Builtin
@signature()
def get_pagesize():
    return Integer(rffi.r_long(asmbuf_get_pagesize()))

module = Module(u'mman', {
    u"get_pagesize": get_pagesize,
    u"Asmbuf": Asmbuf.interface
}, frozen=True)
