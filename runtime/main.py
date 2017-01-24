from rpython.rlib import jit
from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
import vectormath
from evaluator.loader import TraceEntry
import uv_stream
import base
import space
import time
import module_resolution
import os
import pathobj
import rlibuv as uv
from stdlib import api # XXX: perhaps give every module an init?
                       # Probably better way is to move the path resolution from api into here.
import core
import uv_logging

@jit.dont_look_inside # cast_ptr_to_adr
def wakeup_sleeper(handle):
    ec = core.get_ec()

    task = ec.uv_sleepers.pop( rffi.cast_ptr_to_adr(handle) )
    ec.enqueue(task)

    uv.timer_stop(handle)
    uv.close(rffi.cast(uv.handle_ptr, handle), uv.free)

inf = float("inf")

def new_entry_point(config, default_lever_path=u''):
    space.importer_poststage(base.module)
    def entry_point(raw_argv):
        lever_path = os.environ.get('LEVER_PATH')
        if lever_path is None:
            lever_path = pathobj.parse(default_lever_path)
        else:
            lever_path = pathobj.os_parse(lever_path.decode('utf-8'))
        lever_path = pathobj.concat(pathobj.getcwd(), lever_path)
        
        # This should happen only once.
        uv_loop = uv.default_loop()
        uv_idler = uv.malloc_bytes(uv.idle_ptr, uv.handle_size(uv.IDLE))
        uv.idle_init(uv_loop, uv_idler)

        uv_stdin  = initialize_stdio(uv_loop, 0, 1)
        uv_stdout = initialize_stdio(uv_loop, 1, 0)
        uv_stderr = initialize_stdio(uv_loop, 2, 0)

        base.module.setattr_force(u"stdin", uv_stdin)
        base.module.setattr_force(u"stdout", uv_stdout)
        base.module.setattr_force(u"stderr", uv_stderr)
        base.module.setattr_force(u"runtime_path", lever_path)

        ec = core.init_executioncontext(config, lever_path, uv_loop, uv_idler)
        g.log = log = uv_logging.Logger(ec, uv_stdout, uv_stderr)
        api.init(lever_path)
        vectormath.init_random()

        argv = [normal_startup]
        for arg in raw_argv[1:]:
            argv.append(space.String(arg.decode('utf-8')))
        core.schedule(argv)

        uv.run(ec.uv_loop, uv.RUN_DEFAULT)

        #uv.loop_close(ec.uv_loop)

        uv.tty_reset_mode()
        log.last_chance_logging()
        return ec.exit_status
    return entry_point

@space.Builtin
def normal_startup(argv):
    if len(argv) > 0:
        main_script = argv[0]
    else:
        main_script = pathobj.concat(core.get_ec().lever_path, pathobj.parse(u"app/main.lc"))
        main_script = space.String(pathobj.os_stringify(main_script))
    module = module_resolution.start(main_script)
    try:
        main_func = module.getattr(u"main")
    except space.Unwinder as unwinder:
        pass # in this case main_func just isn't in the module.
    else:
        main_func.call([space.List(argv)])
    return space.null

class Suspended(object):
    _immutable_fields_ = ['wakeup', 'greenlet']
    def __init__(self, wakeup, greenlet):
        assert isinstance(greenlet, Greenlet)
        self.wakeup = wakeup
        self.greenlet = greenlet

@base.builtin
def sleep(argv):
    if len(argv) == 1:
        return sleep_greenlet(argv)
    elif len(argv) == 2:
        return sleep_callback(argv)
    else:
        raise space.OldError(u"expected 1 or 2 arguments to sleep(), got %d" % len(argv))

@space.signature(space.Float)
@jit.dont_look_inside # cast_ptr_to_adr
def sleep_greenlet(duration):
    ec = core.get_ec()
    if ec.current == ec.eventloop:
        raise space.OldError(u"bad context for greenlet sleep")
    assert ec.current.is_exhausted() == False

    uv_sleeper = uv.malloc_bytes(uv.timer_ptr, uv.handle_size(uv.TIMER))
    ec.uv_sleepers[rffi.cast_ptr_to_adr(uv_sleeper)] = ec.current
    uv.timer_init(ec.uv_loop, uv_sleeper)
    uv.timer_start(uv_sleeper, wakeup_sleeper, int(duration.number*1000), 0)

    return core.switch([ec.eventloop])

@space.signature(space.Float, space.Object)
@jit.dont_look_inside # cast_ptr_to_adr
def sleep_callback(duration, func):
    ec = core.get_ec()

    uv_sleeper = uv.malloc_bytes(uv.timer_ptr, uv.handle_size(uv.TIMER))
    ec.uv_sleepers[rffi.cast_ptr_to_adr(uv_sleeper)] = core.to_greenlet([func])
    uv.timer_init(ec.uv_loop, uv_sleeper)
    uv.timer_start(uv_sleeper, wakeup_sleeper, int(duration.number*1000), 0)
    return space.null


# This is a rare case when it's better to do nothing than
# something, even if it means that we won't get any
# diagnostics of the error.
def initialize_stdio(uv_loop, fd, readable):
    from uv_stream import TTY, Pipe
    from stdlib.fs import File, ReadStream, WriteStream
    handle_type = uv.guess_handle(fd)
    if handle_type == uv.TTY:
        tty = lltype.malloc(uv.tty_ptr.TO, flavor="raw", zero=True)
        status = uv.tty_init(uv_loop, tty, fd, readable)
        if status < 0:
            lltype.free(tty, flavor='raw')
            return space.null
        return TTY(tty, fd)
    elif handle_type == uv.NAMED_PIPE:
        pipe = lltype.malloc(uv.pipe_ptr.TO, flavor="raw", zero=True)
        status = uv.pipe_init(uv_loop, pipe, 1)
        if status >= 0:
            status = uv.pipe_open(pipe, fd)
        if status < 0:
            lltype.free(pipe, flavor='raw')
            return space.null
        return Pipe(pipe)
    elif handle_type == uv.FILE:
        if readable != 0:
            return ReadStream(File(fd), 0)
        else:
            return WriteStream(File(fd), 0)
    else:
        return space.null
