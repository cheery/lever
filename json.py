# Just the JSON decoder, because I only need a decoder for now.
from rpython.rlib.unicodedata import unicodedb_6_2_0 as unicodedb
import space
import util

class Stream:
    def __init__(self, source, index):
        self.source = source
        self.index = index

    def get(self):
        return self.source[self.index]

    def skipspace(self):
        while unicodedb.isspace(ord(self.get())):
            self.index += 1

    def advance(self):
        ch = self.get()
        self.index += 1
        return ch

    def shift(self, ch):
        if self.get() == ch:
            self.advance()
            return True
        return False

    def expect(self, ch):
        if not self.shift(ch):
            raise space.Error(u"JSON decode expected '%s', got '%s'" % (ch, self.get()))

def decode(stream):
    stream.skipspace()
    if stream.shift(u'{'):
        dct = space.Dict()
        if stream.shift(u'}'):
            return dct
        decode_pair(stream, dct)
        while stream.shift(u','):
            decode_pair(stream, dct)
            stream.skipspace()
        stream.skipspace()
        stream.expect(u'}')
        return dct
    if stream.shift(u'['):
        lst = []
        if stream.shift(u']'):
            return space.List(lst)
        lst.append(decode(stream))
        while stream.shift(u','):
            lst.append(decode(stream))
            stream.skipspace()
        stream.skipspace()
        stream.expect(u']')
        return space.List(lst)
    if stream.get() == u'"':
        return decode_string(stream)
    if stream.shift(u'f'):
        stream.expect(u'a')
        stream.expect(u'l')
        stream.expect(u's')
        stream.expect(u'e')
        return space.false
    if stream.shift(u't'):
        stream.expect(u'r')
        stream.expect(u'u')
        stream.expect(u'e')
        return space.true
    if stream.shift(u'n'):
        stream.expect(u'u')
        stream.expect(u'l')
        stream.expect(u'l')
        return space.null
    if stream.shift(u'-'):
        sign = -1
    else:
        sign = +1
    num = digits(stream)
    if stream.shift(u'.'):
        num += u'.' + digits(stream)
        if stream.get() in u'eE':
            raise space.Error(u"XXX")
        return space.Float(float(num.encode('utf-8')))
    else:
        if stream.get() in u'eE':
            raise space.Error(u"XXX")
        return space.Integer(sign*int(num.encode('utf-8')))
    raise space.Error(u"JSON decode error at %s" % stream.get())

def decode_pair(stream, dct):
    stream.skipspace()
    key = decode_string(stream)
    stream.skipspace()
    stream.expect(u':')
    stream.skipspace()
    val = decode(stream)
    dct.setitem(key, val)

def decode_string(stream):
    string = u''
    stream.expect(u'"')
    while not stream.shift(u'"'):
        ch = stream.advance()
        if ch == u'\\':
            ch = stream.advance()
            string += escape_ch(ch)
        else:
            string += ch
    return space.String(string)

def escape_ch(ch):
    if ch == u'"':
        return u'"'
    if ch == u'\\':
        return u'\\'
    if ch == u'\/':
        return u'/'
    if ch == u'b':
        return u'\b'
    if ch == u'f':
        return u'\f'
    if ch == u'n':
        return u'\n'
    if ch == u'r':
        return u'\r'
    if ch == u't':
        return u'\t'
    raise space.Error(u"JSON decode error")

def digits(stream):
    res = u''
    while stream.get() in u'0123456789':
        res += stream.advance()
    return res

def read_file(path):
    source = util.read_file(path)
    stream = Stream(source, 0)
    return decode(stream)
