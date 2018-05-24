from rpython.rlib import rstring
from rpython.rlib.objectmodel import compute_hash
from rpython.rlib.rstring import UnicodeBuilder, split, rsplit
from rpython.rlib.unicodedata import unicodedb_6_2_0 as unicodedb
from common import *

@method(String.interface, op_eq)
def String_eq(a, b):
    a = cast(a, String)
    b = cast(b, String)
    if a.string_val == b.string_val:
        return true
    else:
        return false

@method(String.interface, op_hash)
def String_hash(a):
    a = cast(a, String)
    return fresh_integer(compute_hash(a.string_val))

@method(String.interface, op_in)
def String_in(i, a):
    i = cast(i, String).string_val
    a = cast(a, String).string_val
    if i in a:
        return true
    else:
        return false

@method(String.interface, op_getitem)
def String_getitem(a, index):
    a = cast(a, String)
    index = cast(a, Integer).toint()
    return String(a.string_val[index])

@getter(List.interface, u"length")
def List_get_length(a):
    return fresh_integer(len(a.string_val))

@method(String.interface, op_iter)
def String_iter(a):
    return StringIterator(0, a.string_val)

class StringIterator(Iterator):
    interface = Iterator.interface
    def __init__(self, index, string_val):
        self.index = index
        self.string_val = string_val

    def next(self):
        if self.index < len(self.string_val):
            k = StringIterator(self.index+1, self.string_val)
            return String(self.string_val[self.index]), k
        raise StopIteration()

@method(String.interface, op_cmp)
def String_cmp(a, b):
    a = cast(a, String).string_val
    b = cast(b, String).string_val
    if a < b:
        return fresh_integer(-1)
    elif a > b:
        return fresh_integer(+1)
    else:
        return fresh_integer(0)

@method(String.interface, op_concat)
def String_concat(a, b):
    a = cast(a, String)
    b = cast(b, String)
    return String(a.string_val + b.string_val)

@method(String.interface, op_stringify)
def String_stringify(a):
    return cast(a, String)

@attr_method(String.interface, u"count")
def String_count(a, ch):
    a = cast(a, String).string_val
    ch = cast(ch, String).string_val
    if len(ch) != 1:
        raise error(e_PartialOnArgument())
    count = 0
    x = ch[0]
    for ch in a:
        if ch == x:
            count += 1
    return fresh_integer(count)

@attr_method(String.interface, u"join")
def String_join(string, seq):
    string = cast(string, String).string_val
    iterator = cast(call(op_iter, [seq]), Iterator)
    strings = []
    while True:
        try:
            x, iterator = iterator.next()
        except StopIteration:
            break
        x = cast(x, String).string_val
        strings.append(x)
    return String(string.join(strings))

@attr_method(String.interface, u"is_lower")
def String_is_lower(string):
    string = cast(string, String).string_val
    for ch in string:
        if not unicodedb.islower(ord(ch)):
            return false
    if len(string) == 0:
        return false
    return true

@attr_method(String.interface, u"is_upper")
def String_is_upper(string):
    string = cast(string, String).string_val
    for ch in string:
        if not unicodedb.isupper(ord(ch)):
            return false
    if len(string) == 0:
        return false
    return true

@attr_method(String.interface, u"is_alpha")
def String_is_alpha(string):
    string = cast(string, String).string_val
    for ch in string:
        if not unicodedb.isalpha(ord(ch)):
            return false
    if len(string) == 0:
        return false
    return true

@attr_method(String.interface, u"is_digit")
def String_is_digit(string, base=fresh_integer(10)):
    string = cast(string, String).string_val
    base = cast(base, Integer).toint()
    if not 0 <= base <= 36:
        raise error(e_PartialOnArgument())
#       raise space.unwind(space.LError(u"is_digit base not in range .:36")) 
    for ch in string:
        if not 0 <= as_alphadigit_i(ord(ch)) < base:
            return false
    if len(string) == 0:
        return false
    return true

def as_alphadigit_i(index):
    if ord('0') <= index <= ord('9'):
        return index - ord('0')
    if ord('A') <= index <= ord('Z'):
        return index - ord('A') + 10
    if ord('a') <= index <= ord('z'):
        return index - ord('a') + 10
    return -1

@attr_method(String.interface, u"is_space")
def String_is_space(string):
    string = cast(string, String).string_val
    for ch in string:
        if not unicodedb.isspace(ord(ch)):
            return false
    if len(string) == 0:
        return false
    return true

@attr_method(String.interface, u"startswith")
def String_startswith(string, prefix):
    string = cast(string, String).string_val
    prefix = cast(prefix, String).string_val
    if string.startswith(prefix):
        return true
    else:
        return false

@attr_method(String.interface, u"endswith")
def String_endswith(string, postfix):
    string = cast(string, String).string_val
    postfix = cast(postfix, String).string_val
    if string.endswith(postfix):
        return true
    else:
        return false

@attr_method(String.interface, u"upper")
def String_upper(string):
    string = cast(string, String).string_val
    return String(string_upper(string))

def string_upper(string):
    b = UnicodeBuilder()
    for ch in string:
        b.append(unichr(unicodedb.toupper(ord(ch))))
    return b.build()

@attr_method(String.interface, u"lower")
def String_lower(string):
    string = cast(string, String).string_val
    return String(string_lower(string))

def string_lower(string):
    b = UnicodeBuilder()
    for ch in string:
        b.append(unichr(unicodedb.tolower(ord(ch))))
    return b.build()

@attr_method(String.interface, u"replace")
def String_replace(a, b, c):
    a = cast(a, String).string_val
    b = cast(b, String).string_val
    c = cast(c, String).string_val
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

@attr_method(String.interface, u"split")
def String_split(string, sep, maxsplit=fresh_integer(-1)):
    string = cast(string, String).string_val
    sep = cast(sep, String).string_val
    out = []
    m = cast(maxsplit, Integer).toint()
    for s in split(string, sep, m):
        out.append(String(s))
    return List(out)

@attr_method(String.interface, u"rsplit")
def String_rsplit(string, sep, maxsplit=fresh_integer(-1)):
    string = cast(string, String).string_val
    sep = cast(sep, String).string_val
    out = []
    m = cast(maxsplit, Integer).toint()
    for s in rsplit(string, sep, m):
        out.append(String(s))
    return List(out)

@attr_method(String.interface, u"ljust")
def String_ljust(string, width, fillchar=String(u' ')):
    string = cast(string, String).string_val
    width = cast(width, Integer).toint()
    fill = cast(fillchar, String).string_val
    if len(fill) != 1:
        raise error(e_PartialOnArgument())
    c = max(0, width - len(string))
    return String(string + fill*c)

@attr_method(String.interface, u"rjust")
def String_rjust(string, width, fillchar=String(u' ')):
    string = cast(string, String).string_val
    width = cast(width, Integer).toint()
    fill = cast(fillchar, String).string_val
    if len(fill) != 1:
        raise error(e_PartialOnArgument())
    c = max(0, width - len(string))
    return String(fill*c + string)

@attr_method(String.interface, u"center")
def String_center(string, width, fillchar=String(u' ')):
    string = cast(string, String).string_val
    width = cast(width, Integer).toint()
    fill = cast(fillchar, String).string_val
    if len(fill) != 1:
        raise error(e_PartialOnArgument())
    c = max(0, width - len(string))
    lhs = (c&1)+c/2
    rhs = c/2
    return String(fill*lhs + string + fill*rhs)

@attr_method(String.interface, u"repeat")
def String_repeat(string, count):
    string = cast(string, String).string_val
    count = cast(count, Integer).toint()
    return String(string * count)
