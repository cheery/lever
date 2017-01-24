from rpython.rtyper.lltypesystem import rffi, lltype, llmemory
from stdlib import fs
import core
import space
import rlibuv as uv
import uv_stream
import uv_callback

class Logger:
    def __init__(self, ec, stdout, stderr):
        # You can attach a queue to log stuff with a "register_logger(queue)"
        self.loggers = []
        self.ec = ec
        self.stdout = stdout
        self.stderr = stderr

    def log(self, which, obj):
        entry = space.Exnihilo()
        entry.setattr(u"type", space.String(which))
        entry.setattr(u"value", obj)
        for logger in list(self.loggers):
            if logger.closed:
                self.loggers.remove(logger)
            else:
                logger.append(entry)
        return len(self.loggers)

    def other(self, which, obj):
        if self.log(which, obj) == 0:
            std = self.stderr if which != u"info" else self.stdout
            if which == u"info" and isinstance(obj, space.List):
                sep = u''
                out = u""
                for arg in obj.contents:
                    if isinstance(arg, space.String):
                        string = arg.string
                    else:
                        string = arg.repr()
                    out += sep + string
                    sep = u' '
                obj = space.String(out)
            if isinstance(obj, space.String):
                data = obj.string.encode('utf-8') + "\n"
            else:
                data = obj.repr().encode('utf-8') + "\n"
            self.write_message(std, data)

    def exception(self, exception):
        if self.log(u"exception", exception) == 0:
            import base
            self.write_message(self.stderr,
                base.format_traceback_raw(exception).encode('utf-8') + "\n")

    def last_chance_logging(self):
        loggers, self.loggers = self.loggers, []
        # last chance logging
        # at this point it is best-effort.
        try:
            if len(loggers) > 0:
                for item in loggers[0].items:
                    which = item.getattr(u"type")
                    value = item.getattr(u"value")
                    which = space.cast(which, space.String, u"last_chance_logging")
                    if which.string != u"exception":
                        continue
                    self.exception(value)
        except space.Unwinder as unwinder:
            self.exception(unwinder.exception)

    # Just like in the initialize_stdio()
    # Here we also ignore error messages.
    # If you cannot log them out, what else can you do?
    # TODO: Some day, make the logging work across threads.
    #       Maybe it should be the day when we'll get STM.
    def write_message(self, std, text):
        if core.get_ec() != self.ec: # Just discard those damn messages if
            return                   # they come up in wrong thread.

        array = space.to_uint8array(text)
        bufs, nbufs = uv_callback.obj2bufs(array)
        if isinstance(std, fs.WriteStream) and not std.fileobj.closed:
            fd = std.fileobj.fd
            req = lltype.malloc(uv.fs_ptr.TO, flavor='raw', zero=True)
            _ = uv.fs_write(self.ec.uv_loop, req, fd,
                bufs, nbufs, std.offset, lltype.nullptr(uv.fs_cb.TO))
            if rffi.r_long(req.c_result) > 0:
                std.offset += rffi.r_long(req.c_result)
            lltype.free(bufs, flavor="raw")
            lltype.free(req, flavor="raw")
        elif isinstance(std, uv_stream.Stream) and not std.closed:
            stream = std.stream
            req = lltype.malloc(uv.write_ptr.TO, flavor='raw', zero=True)
            req.c_data = rffi.cast(rffi.VOIDP, bufs)
            res = uv.write(req, stream, bufs, nbufs, _logging_write_callback_)
            if rffi.r_long(res) < 0:
                lltype.free(bufs, flavor="raw")
                lltype.free(req, flavor="raw")
        else:
            return

def _logging_write_callback_(write_req, status):
    lltype.free(write_req.c_data, flavor="raw")
    lltype.free(write_req, flavor="raw")
