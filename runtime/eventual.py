import py
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from rpython.translator.tool.cbuild import ExternalCompilationInfo
cdir = py.path.local(__file__) / ".."

eci = ExternalCompilationInfo(
    include_dirs = [
    ],
    includes = [
        cdir / "eventual.h"
    ],
    separate_module_files = [
        cdir / "eventual.c",
    ]
)

def llexternal(name, args, result, **kwds):
    return rffi.llexternal(name, args, result,
        compilation_info=eci, **kwds)

# To et_sizeof()
MAIN_LOOP = 0

et_sizeof = llexternal("et_sizeof", [rffi.INT], rffi.SIZE_T)
et_init   = llexternal("et_init",   [rffi.VOIDP], rffi.INT)
et_notify = llexternal("et_notify", [rffi.VOIDP], rffi.INT)
et_wait   = llexternal("et_wait",   [rffi.VOIDP, rffi.LONG], rffi.INT)

INFINITE = -1
