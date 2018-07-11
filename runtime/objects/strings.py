from rpython.rlib import rstring
from rpython.rlib.objectmodel import compute_hash
from rpython.rlib.rstring import UnicodeBuilder, split, rsplit
from rpython.rlib.unicodedata import unicodedb_6_2_0 as unicodedb
from core import *

@method(String, op_eq, 1)
def String_eq(a, b):
    a = cast(a, String)
    b = cast(b, String)
    return wrap(a.string == b.string)

@method(String, op_hash, 1)
def String_hash(a, w_hash):
    a = cast(a, String)
    return wrap(compute_hash(a.string))

@method(String, op_in, 1)
def String_in(i, a):
    i = cast(i, String).string
    a = cast(a, String).string
    return wrap(i in a)

@method(String, op_getitem, 1)
def String_getitem(a, index):
    a = cast(a, String)
    index = unwrap_int(a)
    return String(a.string[index])

@getter(String, u"length", 1)
def String_get_length(a):
    return wrap(len(a.string))

@conversion_to(String, IteratorKind)
def String_iter(a):
    return StringIterator(0, a.string)

class StringIterator(Iterator):
    def __init__(self, index, string):
        self.index = index
        self.string = string

    def next(self):
        if self.index < len(self.string):
            k = StringIterator(self.index+1, self.string)
            return String(self.string[self.index]), k
        raise StopIteration()

@method(String, op_cmp, 1)
def String_cmp(a, b):
    a = cast(a, String).string
    b = cast(b, String).string
    if a < b:
        return wrap(-1)
    elif a > b:
        return wrap(+1)
    else:
        return wrap(0)

@method(String, op_concat, 1)
def String_concat(a, b):
    a = cast(a, String)
    b = cast(b, String)
    return String(a.string + b.string)

@method(String, op_stringify, 1)
def String_stringify(a):
    return cast(a, String)

@attr_method(String, u"count", 1)
def String_count(a, ch):
    a = cast(a, String).string
    ch = cast(ch, String).string
    if len(ch) != 1:
        raise error(e_PreconditionFailed)
    count = 0
    x = ch[0]
    for ch in a:
        if ch == x:
            count += 1
    return wrap(count)

@attr_method(String, u"join", 1)
def String_join(string, seq):
    string = cast(string, String).string
    strings = []
    for item in iterate(seq):
        strings.append(cast(item, String).string)
    return String(string.join(strings))

@attr_method(String, u"is_lower", 1)
def String_is_lower(string):
    string = cast(string, String).string
    for ch in string:
        if not unicodedb.islower(ord(ch)):
            return false
    return wrap(len(string) != 0)

@attr_method(String, u"is_upper", 1)
def String_is_upper(string):
    string = cast(string, String).string
    for ch in string:
        if not unicodedb.isupper(ord(ch)):
            return false
    return wrap(len(string) != 0)

@attr_method(String, u"is_alpha", 1)
def String_is_alpha(string):
    string = cast(string, String).string
    for ch in string:
        if not unicodedb.isalpha(ord(ch)):
            return false
    return wrap(len(string) != 0)

@attr_method(String, u"is_digit", 1)
def String_is_digit(string, base=wrap(10)):
    string = cast(string, String).string
    base = unwrap_int(base)
    if not 0 <= base <= 36:
        raise error(e_PreconditionFailed)
#       raise ... u"is_digit base not in range .:36"
    for ch in string:
        if not 0 <= as_alphadigit_i(ord(ch)) < base:
            return false
    return wrap(len(string) != 0)

def as_alphadigit_i(index):
    if ord('0') <= index <= ord('9'):
        return index - ord('0')
    if ord('A') <= index <= ord('Z'):
        return index - ord('A') + 10
    if ord('a') <= index <= ord('z'):
        return index - ord('a') + 10
    return -1

@attr_method(String, u"is_space", 1)
def String_is_space(string):
    string = cast(string, String).string
    for ch in string:
        if not unicodedb.isspace(ord(ch)):
            return false
    return wrap(len(string) != 0)

@attr_method(String, u"startswith", 1)
def String_startswith(string, prefix):
    string = cast(string, String).string
    prefix = cast(prefix, String).string
    return wrap(string.startswith(prefix))

@attr_method(String, u"endswith", 1)
def String_endswith(string, postfix):
    string = cast(string, String).string
    postfix = cast(postfix, String).string
    return wrap(string.endswith(postfix))

@attr_method(String, u"upper", 1)
def String_upper(string):
    string = cast(string, String).string
    return String(string_upper(string))

def string_upper(string):
    b = UnicodeBuilder()
    for ch in string:
        b.append(unichr(unicodedb.toupper(ord(ch))))
    return b.build()

@attr_method(String, u"lower", 1)
def String_lower(string):
    string = cast(string, String).string
    return String(string_lower(string))

def string_lower(string):
    b = UnicodeBuilder()
    for ch in string:
        b.append(unichr(unicodedb.tolower(ord(ch))))
    return b.build()

@attr_method(String, u"replace", 1)
def String_replace(a, b, c):
    a = cast(a, String).string
    b = cast(b, String).string
    c = cast(c, String).string
    return String(rstring.replace(a, b, c))

# TODO: Consider whether this is still used
#def escape_string(string):
#    out = UnicodeBuilder()
#    out.append(u'"')
#    for ch in string:
#        n = ord(ch)
#        if 0x20 <= n and n <= 0x7E or 0xFF < n: # remove the last part in cond if you don't want
#            if ch == u'\\':                     # unicode printed out for some reason.
#                ch = u'\\\\'
#            elif ch == u'"':
#                ch = u'\\"'
#        else:
#            #if n <= 0xFF:
#            c = u"0123456789abcdef"[n >> 4  & 15]
#            d = u"0123456789abcdef"[n       & 15]
#            ch = u'x' + c + d
#            #else: # for unicode escapes.
#            #    a = u"0123456789abcdef"[n >> 12]
#            #    b = u"0123456789abcdef"[n >> 8  & 15]
#            #    c = u"0123456789abcdef"[n >> 4  & 15]
#            #    d = u"0123456789abcdef"[n       & 15]
#            #    ch = u'u' + a + b + c + d
#            ch = u'\\' + character_escapes.get(n, ch)
#        out.append(ch)
#    out.append(u'"')
#    return out.build()
#
#character_escapes = {8: u'b', 9: u't', 10: u'n', 12: u'f', 13: u'r'}

@attr_method(String, u"split", 1)
def String_split(string, sep, maxsplit=wrap(-1)):
    string = cast(string, String).string
    sep = cast(sep, String).string
    out = []
    m = unwrap_int(maxsplit)
    for s in split(string, sep, m):
        out.append(String(s))
    return List(out)

@attr_method(String, u"rsplit", 1)
def String_rsplit(string, sep, maxsplit=wrap(-1)):
    string = cast(string, String).string
    sep = cast(sep, String).string
    out = []
    m = unwrap_int(maxsplit)
    for s in rsplit(string, sep, m):
        out.append(String(s))
    return List(out)

@attr_method(String, u"ljust", 1)
def String_ljust(string, width, fillchar=String(u' ')):
    string = cast(string, String).string
    width = unwrap_int(width)
    fill = cast(fillchar, String).string
    if len(fill) != 1:
        raise error(e_PreconditionFailed)
    c = max(0, width - len(string))
    return String(string + fill*c)

@attr_method(String, u"rjust", 1)
def String_rjust(string, width, fillchar=String(u' ')):
    string = cast(string, String).string
    width = unwrap_int(width)
    fill = cast(fillchar, String).string
    if len(fill) != 1:
        raise error(e_PreconditionFailed)
    c = max(0, width - len(string))
    return String(fill*c + string)

@attr_method(String, u"center", 1)
def String_center(string, width, fillchar=String(u' ')):
    string = cast(string, String).string
    width = unwrap_int(width)
    fill = cast(fillchar, String).string
    if len(fill) != 1:
        raise error(e_PreconditionFailed)
    c = max(0, width - len(string))
    lhs = (c&1)+c/2
    rhs = c/2
    return String(fill*lhs + string + fill*rhs)

@attr_method(String, u"repeat", 1)
def String_repeat(string, count):
    string = cast(string, String).string
    count = unwrap_int(count)
    return String(string * count)

variables = {
}
