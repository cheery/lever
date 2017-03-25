## Just the JSON decoder, because I only need a decoder for now.
#from rpython.rlib.unicodedata import unicodedb_6_2_0 as unicodedb
from rpython.rlib.listsort import make_timsort_class
from rpython.rlib import rfile
from rpython.rlib.rstring import UnicodeBuilder
from rpython.rlib.objectmodel import specialize, always_inline
from space import *
from space import numbers
from stdlib import fs
import space
import pathobj
import os

module = Module(u'json', {}, frozen=True)

def builtin(deco):
    def _deco_(fn):
        name = fn.__name__.rstrip('_').decode('utf-8')
        module.setattr_force(name, Builtin(deco(fn), name))
        return fn
    return _deco_

@builtin(signature(Object, Object, Dict, optional=1))
def write_file(pathname, obj, config):
    name = pathobj.os_stringify(pathname).encode('utf-8')
    try:
        fd = rfile.create_file(name, "wb")
        try:
            # TODO: sort of defeats the purpose of
            # incremental encoder.
            fd.write(configured_stringify(obj, config).encode('utf-8'))
            fd.write('\n')
        finally:
            fd.close()
    except IOError as error:
        message = os.strerror(error.errno).decode('utf-8')
        raise OldError(u"%s: %s" % (pathobj.stringify(pathname), message))
    return null

@builtin(signature(Object, Dict, optional=1))
def write_string(obj, config):
    return space.String(configured_stringify(obj, config))

def configured_stringify(obj, config):
    if config is None:
        ub = UnicodeBuilder()
        quick_stringify(ub, obj)
        return ub.build()
    margin = space.to_int(get_config(config, u"margin", space.Integer(80)))
    scan = Scanner(Printer(margin))
    scan.indent = space.to_int(get_config(config, u"indent", space.Integer(2)))
    scan.sort_keys = space.is_true(get_config(config, u"sort_keys", space.false))
    stringify(scan, obj)
    scan.finish()
    return scan.printer.result.build()

def get_config(config, text, default):
    return config.data.get(space.String(text), default)

def quick_stringify(ub, obj):
    if isinstance(obj, space.Dict):
        ub.append(u"{")
        more = False
        for key, value in obj.data.iteritems():
            if not isinstance(key, String):
                raise unwind(LError(
                    u"json supports only strings as keys: "
                    + key.repr()))
            if more:
                ub.append(u",")
            ub.append(escape_string(key.string))
            ub.append(u':')
            quick_stringify(ub, value)
            more = True
        ub.append(u"}")
    elif isinstance(obj, space.List):
        ub.append(u"[")
        more = False
        for item in obj.contents:
            if more:
                ub.append(u",")
            quick_stringify(ub, item)
            more = True
        ub.append(u"]")
    elif isinstance(obj, space.String):
        ub.append(escape_string(obj.string))
    elif isinstance(obj, space.Integer):
        ub.append(numbers.integer_to_string(obj.value, 10))
    elif isinstance(obj, space.Float):
        ub.append(numbers.float_to_string(obj.number))
    elif obj is space.null:
        ub.append(u"null")
    elif obj is space.true:
        ub.append(u"true")
    elif obj is space.false:
        ub.append(u"false")
    else:
        raise unwind(LError(u"no handler for: " + obj.repr()))

def stringify(scan, obj):
    if isinstance(obj, space.Dict):
        scan.left().text(u"{").blank(u"", scan.indent)
        more = False
        if scan.sort_keys:
            pairs = []
            for key, value in obj.data.iteritems():
                if not isinstance(key, String):
                    raise unwind(LError(
                        u"json supports only strings as keys: "
                        + key.repr()))
                pairs.append((key, value))
            sorter = JSONKeySort(pairs, len(pairs))
            sorter.sort()
            for key, value in sorter.list:
                if more:
                    scan.text(u",").blank(u" ", scan.indent)
                scan.left()
                scan.text(escape_string(key.string)+u': ')
                stringify(scan, value)
                scan.right()
                more = True
        else:
            for key, value in obj.data.iteritems():
                if not isinstance(key, String):
                    raise unwind(LError(
                        u"json supports only strings as keys: "
                        + key.repr()))
                if more:
                    scan.text(u",").blank(u" ", scan.indent)
                scan.left()
                scan.text(escape_string(key.string)+u': ')
                stringify(scan, value)
                scan.right()
                more = True
        scan.blank(u"", 0).text(u"}").right()
    elif isinstance(obj, space.List):
        scan.left().text(u"[").blank(u"", scan.indent)
        more = False
        for item in obj.contents:
            if more:
                scan.text(u",").blank(u" ", scan.indent)
            stringify(scan, item)
            more = True
        scan.blank(u"", 0).text(u"]").right()
    elif isinstance(obj, space.String):
        scan.text(escape_string(obj.string))
    elif isinstance(obj, space.Integer):
        scan.text(numbers.integer_to_string(obj.value, 10))
    elif isinstance(obj, space.Float):
        scan.text(numbers.float_to_string(obj.number))
    elif obj is space.null:
        scan.text(u"null")
    elif obj is space.true:
        scan.text(u"true")
    elif obj is space.false:
        scan.text(u"false")
    else:
        raise unwind(LError(u"no handler for: " + obj.repr()))

TimSort = make_timsort_class()
class JSONKeySort(TimSort):
    def lt(self, a, b):
        return a[0].string < b[0].string

# This is the easiest point of failure in your stringifier program.
def escape_string(string):
    out = UnicodeBuilder()
    out.append(u'"')
    for ch in string:
        n = ord(ch)
        if 0x20 <= n and n <= 0x7E or 0xFF < n: # remove the last part in cond if you don't want
            if ch == u'\\':                     # unicode printed out for some reason.
                ch = u'\\\\'
            elif ch == u'"':
                ch = u'\\"'
        else:
            a = u"0123456789abcdef"[n >> 12]
            b = u"0123456789abcdef"[n >> 8  & 15]
            c = u"0123456789abcdef"[n >> 4  & 15]
            d = u"0123456789abcdef"[n       & 15]
            ch = u'u' + a + b + c + d
            ch = u'\\' + character_escapes.get(n, ch)
        out.append(ch)
    out.append(u'"')
    return out.build()

character_escapes = {8: u'b', 9: u't', 10: u'n', 12: u'f', 13: u'r'}

# The scanner runs three line widths before the printer and checks how many
# spaces the blanks and groups take. This allows the printer determine
# whether the line or grouping should be broken into multiple lines.
class Scanner(object):
    def __init__(self, printer):
        self.printer = printer
        self.stream = []
        self.stack = []
        self.lastblank = None
        self.left_total = 1
        self.right_total = 1 # makes sure we won't treat the first
                             # item differently than others.

        self.sort_keys = False
        self.indent = 2

    def left(self):
        return self.scan(Left())

    def right(self):
        return self.scan(Right())

    def blank(self, text, indent):
        return self.scan(Blank(text, indent))

    def text(self, text):
        return self.scan(Text(text))

    def scan(self, x):
        if isinstance(x, Left):
            x.size = -self.right_total
            self.stack.append(x)
        elif isinstance(x, Right):
            if len(self.stack) > 0:
                self.stack.pop().size += self.right_total
        elif isinstance(x, Blank):
            if self.lastblank is not None:
                self.lastblank.size += self.right_total
            self.lastblank = x
            x.size = -self.right_total
            self.right_total += len(x.text)
        elif isinstance(x, Text):
            self.right_total += len(x.text)
        self.stream.append(x)
        while len(self.stream) > 0 and self.right_total - self.left_total > 3*self.printer.margin:
            self.left_total += self.printer.scan(self.stream.pop(0))
        return self

    def finish(self):
        if self.lastblank is not None:              # Well.. of course.
            self.lastblank.size += self.right_total # I didn't figure this out earlier.
        while len(self.stream) > 0:
            self.printer.scan(self.stream.pop(0))

# Printer keeps the track of layout during printing.
class Printer:
    def __init__(self, margin):
        self.margin = margin
        self.layout = Layout(None, margin, False)
        self.spaceleft = margin
        self.spaces = margin
        self.result = UnicodeBuilder()

    def scan(self, x):
        if isinstance(x, Left):
            self.layout = Layout(self.layout,
                self.spaces, x.size < 0 or self.spaceleft < x.size)
        elif isinstance(x, Right):
            if self.layout.parent:
                self.layout = self.layout.parent
        elif isinstance(x, Blank):
            if x.size < 0 or self.spaceleft < x.size or self.layout.force_break:
                self.spaces = self.layout.spaces - x.indent
                self.spaceleft = self.spaces
                self.result.append(u'\n' + u' '*(self.margin - self.spaces))
            else:
                self.result.append(x.text)
                self.spaceleft -= len(x.text)
        elif isinstance(x, Text):
            self.result.append(x.text)
            self.spaceleft -= len(x.text)
        return len(x)

# These small objects are scanner and printer internals.
class Layout(object):
    def __init__(self, parent, spaces, force_break):
        self.parent = parent
        self.spaces = spaces
        self.force_break = force_break

# These objects are mutated by the scanner, so they cannot be
# reused. Users of the pretty printer should not create them themselves.
class ScannerToken:
    def __len__(self):
        return 0

class Text(ScannerToken):
    def __init__(self, text):
        self.text = text

    def __len__(self):
        return len(self.text)

class Left(ScannerToken):
    def __init__(self):
        self.size = 0

class Right(ScannerToken):
    pass

class Blank(ScannerToken):
    def __init__(self, text, indent=0):
        self.text = text
        self.indent = indent
        self.size = 0

    def __len__(self):
        return len(self.text)



@builtin(signature(Object))
def read_file(path):
    sobj = fs.read_file([path])
    assert isinstance(sobj, String)
    return read_string(sobj)

@builtin(signature(String))
def read_string(string):
    stack = []
    ctx = ParserContext()
    state = 0x00
    for ch in string.string:
        cat = catcode[min(ord(ch), 0x7E)]
        state = parse_char(cat, ch, stack, state, ctx)
    state = parse_char(catcode[32], u' ', stack, state, ctx)
    if state != 0x00:
        raise unwind(LError(u"JSON decode error: truncated"))
    if len(ctx.ds) != 1:
        raise unwind(LError(u"JSON decode error: too many objects"))
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
            raise unwind(LError(u"JSON decode error: syntax"))
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
        ctx.ds.append(space.List([]))
    # Push object to ds
    elif action == 0x2:            # push object
        ctx.ds.append(space.Dict())
    elif action == 0x3:            # pop & append
        val = ctx.ds.pop()
        top = ctx.ds[len(ctx.ds)-1]
        assert isinstance(top, List) # we can trust this.
        top.contents.append(val)
    elif action == 0x4:            # pop pop & setitem
        val = ctx.ds.pop()
        key = ctx.ds.pop()
        top = ctx.ds[len(ctx.ds)-1]
        assert isinstance(top, Dict) # again..
        top.data[key] = val
    elif action == 0x5:           # push null
        ctx.ds.append(space.null)
    elif action == 0x6:           # push true
        ctx.ds.append(space.true)
    elif action == 0x7:           # push false
        ctx.ds.append(space.false)
    elif action == 0x8:           # push string
        val = ctx.ss.build()
        ctx.ds.append(space.String(val))
        ctx.ss = UnicodeBuilder()
        ctx.es = UnicodeBuilder()
    elif action == 0x9:
        val = int(ctx.ss.build().encode('utf-8'))    # push int
        ctx.ds.append(space.Integer(val))
        ctx.ss = UnicodeBuilder()
    elif action == 0xA:
        val = float(ctx.ss.build().encode('utf-8'))  # push float
        ctx.ds.append(space.Float(val))
        ctx.ss = UnicodeBuilder()
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
