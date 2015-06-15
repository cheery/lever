"""
    Tokenizer with two-token lookahead stream.
"""
from stream import CStream
from data import Literal

class Error(Exception):
    pass

class L2(object):
    def __init__(self, stream, table):
        self.stream = stream
        self.table = table
        self.first = next_token(self.stream, self.table)
        if self.first is not None:
            self.first.lsp = True
            self.first.rsp = self.stream.is_space()
    
    def advance(self):
        lsp = self.stream.is_space()
        t = self.first
        self.first = next_token(self.stream, self.table)
        if self.first is not None:
            self.first.lsp = lsp
            self.first.rsp = self.stream.is_space()
        return t

    @property
    def filled(self):
        return self.first is not None

    @property
    def position(self):
        if self.filled:
            return self.first.start
        else:
            return self.stream.position

def next_token(stream, table):
    while stream.filled and stream.is_space():
        stream.advance()
    if not stream.filled:
        return None
    if stream.current == u'#':
        while stream.filled and stream.current != u'\n':
            stream.advance()
        return next_token(stream, table)
    start = stream.position
    if stream.is_sym():
        string = stream.advance()
        while stream.is_sym() or stream.is_digit():
            string += stream.advance()
        name = table.get(string, u'symbol')
        return Literal(start, stream.position, name, string)
    elif stream.is_digit():
        string = stream.advance()
        if string == u'0' and stream.filled and stream.current == u'x':
            string += stream.advance()
            while stream.is_hex():
                string += stream.advance()
            return Literal(start, stream.position, u'hex', string)
        while stream.is_digit():
            string += stream.advance()
        if stream.filled and stream.current == u'.':
            string += stream.advance()
            while stream.is_digit():
                string += stream.advance()
            return Literal(start, stream.position, u'float', string)
        return Literal(start, stream.position, u'int', string)
    elif stream.current in (u'"', u"'"):
        terminal = stream.advance()
        string = u""
        while stream.filled and stream.current != terminal:
            if stream.current == u'\\':
                stream.advance()
            string += stream.advance()
        if not stream.filled:
            raise Error(u"%s: Broken string literal" % start.repr())
        assert terminal == stream.advance()
        return Literal(start, stream.position, u'string', string)
    elif stream.current in table:
        string = stream.advance()
        while stream.filled and string + stream.current in table:
            string += stream.advance()
        name = table[string]
        return Literal(start, stream.position, name, string)
    else:
        string = stream.advance()
        return Literal(start, stream.position, u'symbol', string)
