from objects import *
from rpython.rlib import rfile
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rlib.rstring import UnicodeBuilder
from rpython.rlib.rstruct import ieee
from rpython.rtyper.lltypesystem import rffi
import os
import sys

def read_json_file(pathname):
    pathname = cast(pathname, String).string_val
    raw_pathname = pathname.encode('utf-8')
    try:
        fd = rfile.create_file(raw_pathname, 'rb')
        try:
            return read_json_fd(fd)
        finally:
            fd.close()
    except IOError as io:
        message = os.strerror(io.errno)
        os.write(0, message + "\n")
        raise error(e_IOError())

def read_json_fd(fd):
    stack = []
    ctx = ParserContext()
    state = 0x00
    for ch in fd.read().decode('utf-8'):
        cat = catcode[min(ord(ch), 0x7E)]
        state = parse_char(cat, ch, stack, state, ctx)
    state = parse_char(catcode[32], u' ', stack, state, ctx)
    if state != 0x00:
        raise error(e_JSONDecodeError(u"truncated"))
    if len(ctx.ds) != 1:
        raise error(e_JSONDecodeError(u"too many objects"))
    return ctx.ds.pop()

class ParserContext:
    def __init__(self):
        self.ds = [] # data stack
        self.ss = UnicodeBuilder() # string stack
        self.es = UnicodeBuilder() # escape stack

@always_inline
def parse_char(cat, ch, stack, state, ctx):
    while True:
        code = states[state][cat]
        action = code >> 8 & 0xFF
        code   = code      & 0xFF
        if action == 0xFF and code == 0xFF:
            raise error(e_JSONDecodeError(u"syntax error"))
        elif action >= 0x80: # shift
            stack.append(gotos[state])
            action -= 0x80
        if action > 0:
            decode_json(action, ch, ctx)
        if code == 0xFF:
            state = stack.pop()
        else:
            state = code
            return state

@always_inline
def decode_json(action, ch, ctx):
    if action == 0x1:              # push list
        ctx.ds.append(fresh_list())
    # Push object to ds
    elif action == 0x2:            # push object
        ctx.ds.append(fresh_dict())
    elif action == 0x3:            # pop & append
        val = ctx.ds.pop()
        top = ctx.ds[len(ctx.ds)-1]
        assert isinstance(top, List) # we can trust this.
        top.list_val.append(val)
    elif action == 0x4:            # pop pop & setitem
        val = ctx.ds.pop()
        key = ctx.ds.pop()
        top = ctx.ds[len(ctx.ds)-1]
        assert isinstance(top, Dict) # again..
        top.dict_val[key] = val
    elif action == 0x5:           # push null
        ctx.ds.append(null)
    elif action == 0x6:           # push true
        ctx.ds.append(true)
    elif action == 0x7:           # push false
        ctx.ds.append(false)
    elif action == 0x8:           # push string
        val = ctx.ss.build()
        ctx.ds.append(String(val))
        ctx.ss = UnicodeBuilder()
        ctx.es = UnicodeBuilder()
    elif action == 0x9:
        val = int(ctx.ss.build().encode('utf-8'))    # push int
        ctx.ds.append(fresh_integer(val))
        ctx.ss = UnicodeBuilder()
    elif action == 0xA:
        # TODO: Users thank later if we use some
        #       exact decoding for these values.
        raise error(e_JSONDecodeError(u"decimals not implemented"))
        #val = float(ctx.ss.build().encode('utf-8'))  # push float
        #ctx.ds.append(fresh_float(val))
        #ctx.ss = UnicodeBuilder()
    elif action == 0xB:            # push ch to ss
        ctx.ss.append(ch)
    elif action == 0xC:            # push ch to es
        ctx.es.append(ch)
    elif action == 0xD:            # push escape
        ctx.ss.append(unichr(escape_characters[ch]))
    elif action == 0xE:            # push unicode point
        ctx.ss.append(unichr(int(ctx.es.build().encode('utf-8'), 16)))
        ctx.es = UnicodeBuilder()
    else: # This is very unlikely to happen.
        assert False, "JSON decoder bug"

# Non-trivial escape characters. At worst you can
# 'switch' or 'if/else' them into do_action -function.
escape_characters = {'b': 8, 't': 9, 'n': 10, 'f': 12, 'r': 13}

# generated by build_tables.py program: http://github.com/cheery/json_algorithm
states = [
    [ 0xffff, 0x0000, 0x801a, 0xffff, 0xffff, 0x8b29, 0xffff, 0xffff, 0x8b28, 0x8b22, 0xffff, 0xffff, 0xffff, 0x810e, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x8009, 0xffff, 0x8001, 0xffff, 0xffff, 0x8005, 0xffff, 0x8212, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0002, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0003, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0004, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, 0x05ff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0006, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0007, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0008, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, 0x06ff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x000a, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x000b, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x000c, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x000d, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, 0x07ff, ],
    [ 0xffff, 0x000e, 0x801a, 0xffff, 0xffff, 0x8b29, 0xffff, 0xffff, 0x8b28, 0x8b22, 0xffff, 0xffff, 0xffff, 0x810e, 0xffff, 0x0011, 0xffff, 0xffff, 0xffff, 0x8009, 0xffff, 0x8001, 0xffff, 0xffff, 0x8005, 0xffff, 0x8212, 0xffff, ],
    [ 0xffff, 0x000f, 0xffff, 0xffff, 0x0310, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0311, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0x0010, 0x801a, 0xffff, 0xffff, 0x8b29, 0xffff, 0xffff, 0x8b28, 0x8b22, 0xffff, 0xffff, 0xffff, 0x810e, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x8009, 0xffff, 0x8001, 0xffff, 0xffff, 0x8005, 0xffff, 0x8212, 0xffff, ],
    [ 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, ],
    [ 0xffff, 0x0012, 0x801a, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0019, ],
    [ 0xffff, 0x0013, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0014, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0x0014, 0x801a, 0xffff, 0xffff, 0x8b29, 0xffff, 0xffff, 0x8b28, 0x8b22, 0xffff, 0xffff, 0xffff, 0x810e, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x8009, 0xffff, 0x8001, 0xffff, 0xffff, 0x8005, 0xffff, 0x8212, 0xffff, ],
    [ 0xffff, 0x0015, 0xffff, 0xffff, 0x0416, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0419, ],
    [ 0xffff, 0x0016, 0x801a, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0x0017, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0018, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0x0018, 0x801a, 0xffff, 0xffff, 0x8b29, 0xffff, 0xffff, 0x8b28, 0x8b22, 0xffff, 0xffff, 0xffff, 0x810e, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x8009, 0xffff, 0x8001, 0xffff, 0xffff, 0x8005, 0xffff, 0x8212, 0xffff, ],
    [ 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, 0x00ff, ],
    [ 0x0b1a, 0x0b1a, 0x0021, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x001b, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, 0x0b1a, ],
    [ 0xffff, 0xffff, 0x0b1a, 0xffff, 0xffff, 0xffff, 0xffff, 0x0b1a, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0b1a, 0xffff, 0xffff, 0x0d1a, 0xffff, 0x0d1a, 0xffff, 0x0d1a, 0x0d1a, 0xffff, 0x0d1a, 0x801c, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0c1d, 0x0c1d, 0xffff, 0x0c1d, 0x0c1d, 0xffff, 0xffff, 0xffff, 0x0c1d, 0x0c1d, 0x0c1d, 0x0c1d, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0c1e, 0x0c1e, 0xffff, 0x0c1e, 0x0c1e, 0xffff, 0xffff, 0xffff, 0x0c1e, 0x0c1e, 0x0c1e, 0x0c1e, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0c1f, 0x0c1f, 0xffff, 0x0c1f, 0x0c1f, 0xffff, 0xffff, 0xffff, 0x0c1f, 0x0c1f, 0x0c1f, 0x0c1f, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0c20, 0x0c20, 0xffff, 0x0c20, 0x0c20, 0xffff, 0xffff, 0xffff, 0x0c20, 0x0c20, 0x0c20, 0x0c20, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, 0x0eff, ],
    [ 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, 0x08ff, ],
    [ 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x0b23, 0x09ff, 0x0b22, 0x0b22, 0x09ff, 0x09ff, 0x0b25, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x0b25, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0b24, 0x0b24, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0b24, 0x0b24, 0x0aff, 0x0aff, 0x0b25, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0b25, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, ],
    [ 0xffff, 0xffff, 0xffff, 0x0b26, 0xffff, 0x0b26, 0xffff, 0xffff, 0x0b27, 0x0b27, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0b27, 0x0b27, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
    [ 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0b27, 0x0b27, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, 0x0aff, ],
    [ 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x0b23, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x0b25, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x0b25, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, 0x09ff, ],
    [ 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0x0b28, 0x0b22, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, 0xffff, ],
]
gotos = [0, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 15, 255, 15, 255, 19, 255, 21, 255, 23, 255, 21, 255, 255, 26, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255]
catcode = [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 3, 4, 5, 6, 7, 8, 9, 9, 9, 9, 9, 9, 9, 9, 9, 10, 0, 0, 0, 0, 0, 0, 11, 11, 11, 11, 12, 11, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 13, 14, 15, 0, 0, 0, 16, 17, 11, 11, 18, 19, 0, 0, 0, 0, 0, 20, 0, 21, 0, 0, 0, 22, 23, 24, 25, 0, 0, 0, 0, 0, 26, 0, 27, 0]