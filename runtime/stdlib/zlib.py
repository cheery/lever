from space import *
from rpython.rlib import rzlib
from rpython.rtyper.lltypesystem import rffi, lltype

module = Module(u'zlib', {}, frozen=True)

def builtin(fn):
    name = fn.__name__.rstrip('_').decode('utf-8')
    module.setattr_force(name, Builtin(fn, name))
    return fn

@builtin
@signature(Uint8Data, Integer, optional=1)
def crc32(array, start):
    start = rzlib.CRC32_DEFAULT_START if start is None else start.value
    string = array.to_str()
    checksum = rzlib.crc32(string, rffi.r_uint(start))
    return Integer(rffi.r_long(checksum))

@builtin
@signature(Uint8Data, Integer, optional=1)
def adler32(array, start):
    start = rzlib.ADLER32_DEFAULT_START if start is None else start.value
    string = array.to_str()
    checksum = rzlib.adler32(string, rffi.r_uint(start))
    return Integer(rffi.r_long(checksum))

class Compress(Object):
    def __init__(self, stream):
        self.stream = stream

    def __del__(self):
        if self.stream:
            rzlib.deflateEnd(self.stream)
            self.stream = rzlib.null_stream

# TODO: add options handler here.
@Compress.instantiator2(signature())
def Compress_init():
    try:
        level = rzlib.Z_DEFAULT_COMPRESSION
        method = rzlib.Z_DEFLATED
        wbits = rzlib.MAX_WBITS
        memLevel = rzlib.DEF_MEM_LEVEL
        strategy = rzlib.Z_DEFAULT_STRATEGY
        stream = rzlib.deflateInit(level, method, wbits, memLevel, strategy)
        return Compress(stream)
    except rzlib.RZlibError as e:
        raise zlib_error(e.msg)

@Compress.method(u"compress_beta", signature(Compress, Object, Object))
def Compress_compress_beta(self, inp, out):
    stream = self.stream
    i_data  = cast(inp.getattr(u"data"),  Uint8Data, u"inp.data")
    i_start = cast(inp.getattr(u"start"), Integer, u"inp.start").value
    i_stop  = cast(inp.getattr(u"stop"),  Integer, u"inp.stop").value
    if not (0 <= i_start <= i_stop <= i_data.length):
        raise unwind(LTypeError(u"inp.start/stop invalid"))

    o_data  = cast(out.getattr(u"data"),  Uint8Data, u"out.data")
    o_start = cast(out.getattr(u"start"), Integer, u"out.start").value
    o_stop  = cast(out.getattr(u"stop"),  Integer, u"out.stop").value
    if not (0 <= o_start <= o_stop <= o_data.length):
        raise unwind(LTypeError(u"out.start/stop invalid"))

    stream.c_next_in = rffi.ptradd(i_data.uint8data, i_start)
    stream.c_avail_in = rffi.r_uint(i_stop - i_start)
    stream.c_next_out = rffi.ptradd(o_data.uint8data, o_stop)
    stream.c_avail_out = rffi.r_uint(o_data.length - o_stop)
    if i_start == i_stop:
        err = rzlib._deflate(stream, rzlib.Z_FINISH)
    else:
        err = rzlib._deflate(stream, 0)

    if err == rzlib.Z_NEED_DICT:
        raise unwind(LError(u"Z_NEED_DICT"))
    if err == rzlib.Z_BUF_ERROR:
        raise unwind(LError(u"Z_BUF_ERROR"))
    if err == rzlib.Z_OK or err == rzlib.Z_STREAM_END:
        inp.setattr(u"start", Integer(i_stop - rffi.r_long(stream.c_avail_in)))
        out.setattr(u"stop", Integer(rffi.r_long(stream.c_avail_out) + o_stop))
    return null

@Compress.method(u"compress", signature(Compress, Uint8Data))
def Compress_compress(self, array):
    data = array.to_str()
    try:
        # lock
        result = rzlib.compress(self.stream, data)
        # unlock
    except rzlib.RZlibError as e:
        raise zlib_error(e.msg)
    return to_uint8array(result)
    
@Compress.method(u"finish", signature(Compress, Integer, optional=1))
def Compress_finish(self, mode):
    mode = rzlib.Z_FINISH if mode is None else mode.value
    try:
        # lock
        result = rzlib.compress(self.stream, '', rzlib.Z_FINISH)
        if mode == rzlib.Z_FINISH:
            rzlib.deflateEnd(self.stream)
            self.stream = rzlib.null_stream
        # unlock
    except rzlib.RZlibError as e:
        raise zlib_error(e.msg)
    return to_uint8array(result)

class Decompress(Object):
    def __init__(self, stream):
        self.stream = stream

    def __del__(self):
        if self.stream:
            rzlib.inflateEnd(self.stream)
            self.stream = rzlib.null_stream

@Decompress.instantiator2(signature(Integer, optional=1))
def Decompress_init(wbits):
    wbits = rzlib.MAX_WBITS if wbits is None else wbits.value
    try:
        stream = rzlib.inflateInit(wbits)
        return Decompress(stream)
    except rzlib.RZlibError as e:
        raise zlib_error(e.msg)

@Decompress.method(u"decompress_beta", signature(Decompress, Object, Object))
def Decompress_decompress_beta(self, inp, out):
    stream = self.stream
    i_data  = cast(inp.getattr(u"data"),  Uint8Data, u"inp.data")
    i_start = cast(inp.getattr(u"start"), Integer, u"inp.start").value
    i_stop  = cast(inp.getattr(u"stop"),  Integer, u"inp.stop").value
    if not (0 <= i_start <= i_stop <= i_data.length):
        raise unwind(LTypeError(u"inp.start/stop invalid"))

    o_data  = cast(out.getattr(u"data"),  Uint8Data, u"out.data")
    o_start = cast(out.getattr(u"start"), Integer, u"out.start").value
    o_stop  = cast(out.getattr(u"stop"),  Integer, u"out.stop").value
    if not (0 <= o_start <= o_stop <= o_data.length):
        raise unwind(LTypeError(u"out.start/stop invalid"))

    stream.c_next_in = rffi.ptradd(i_data.uint8data, i_start)
    stream.c_avail_in = rffi.r_uint(i_stop - i_start)
    stream.c_next_out = rffi.ptradd(o_data.uint8data, o_stop)
    stream.c_avail_out = rffi.r_uint(o_data.length - o_stop)
    if i_start == i_stop:
        err = rzlib._inflate(stream, rzlib.Z_FINISH)
    else:
        err = rzlib._inflate(stream, 0)

    if err == rzlib.Z_NEED_DICT:
        raise unwind(LError(u"Z_NEED_DICT"))
    if err == rzlib.Z_BUF_ERROR:
        raise unwind(LError(u"Z_BUF_ERROR"))
    if err == rzlib.Z_OK or err == rzlib.Z_STREAM_END:
        inp.setattr(u"start", Integer(i_stop - rffi.r_long(stream.c_avail_in)))
        out.setattr(u"stop", Integer(rffi.r_long(stream.c_avail_out) + o_stop))
    return null

@Decompress.method(u"decompress", signature(Decompress, Uint8Data))
def Decompress_decompress(self, array):
    data = array.to_str()
    try:
        # lock
        result = rzlib.decompress(self.stream, data)
        # finally unlock
    except rzlib.RZlibError as e:
        raise zlib_error(e.msg)
    string, finished, unused_len = result
    assert unused_len == 0
    return to_uint8array(string)

@Decompress.method(u"finish", signature(Decompress))
def Decompress_finish(self):
    try:
        # lock
        result = rzlib.decompress(self.stream, '', rzlib.Z_FINISH)
        # finally unlock
    except rzlib.RZlibError as e:
        raise zlib_error(e.msg)
    string, finished, unused_len = result
    assert unused_len == 0
    return to_uint8array(string)

def zlib_error(msg):
    return unwind(LError(msg.decode('utf-8')))

module.setattr_force(u"Decompress", Decompress.interface)
module.setattr_force(u"Compress", Compress.interface)

for _name in u"""
    MAX_WBITS  DEFLATED  DEF_MEM_LEVEL
    Z_BEST_SPEED  Z_BEST_COMPRESSION  Z_DEFAULT_COMPRESSION
    Z_FILTERED  Z_HUFFMAN_ONLY  Z_DEFAULT_STRATEGY
    Z_FINISH  Z_NO_FLUSH  Z_SYNC_FLUSH  Z_FULL_FLUSH
    ZLIB_VERSION""".split():
    value = getattr(rzlib, _name)
    if isinstance(value, int):
        module.setattr_force(_name, Integer(value))
    elif isinstance(value, str):
        module.setattr_force(_name, String(value.decode('utf-8')))
    else:
        assert False, "add fillup method"
