"""
    Tokenizer with two-token lookahead stream.
"""
from stream import CStream
from data import Literal

default_symtab = {
    u"string": u"string",
    u"symbol": u"symbol",
    u"hex": u"hex",
    u"int": u"int",
    u"float": u"float" }

class Error(Exception):
    pass

class L2(object):
    def __init__(self, stream, table, symtab=default_symtab):
        self.stream = stream
        self.table = table
        self.symtab = symtab
        self.first = next_token(self.stream, self.table, self.symtab)
        if self.first is not None:
            self.first.lsp = True
            self.first.rsp = self.stream.is_space()
    
    def advance(self):
        lsp = self.stream.is_space()
        t = self.first
        self.first = next_token(self.stream, self.table, self.symtab)
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

def next_token(stream, table, symtab):
    while stream.filled and stream.is_space():
        stream.advance()
    if not stream.filled:
        return None
    if stream.current == u'#':
        while stream.filled and stream.current != u'\n':
            stream.advance()
        return next_token(stream, table, symtab)
    start = stream.position
    if stream.is_sym():
        string = stream.advance()
        while stream.is_sym() or stream.is_digit():
            string += stream.advance()
        name = table.get(string, symtab[u'symbol'])
        return Literal(start, stream.position, name, string)
    elif stream.is_digit():
        string = stream.advance()
        if string == u'0' and stream.filled and stream.current == u'x':
            stream.advance()
            string = u""
            while stream.is_hex():
                string += stream.advance()
            return Literal(start, stream.position, symtab[u'hex'], string)
        while stream.is_digit():
            string += stream.advance()
        if stream.filled and stream.current == u'.' and not stream.pair_ahead(table):
            string += stream.advance()
            while stream.is_digit():
                string += stream.advance()
            return Literal(start, stream.position, symtab[u'float'], string)
        return Literal(start, stream.position, symtab[u'int'], string)
    elif stream.current in (u'"', u"'"):
        terminal = stream.advance()
        string = u""
        while stream.filled and stream.current != terminal:
            if stream.current == u'\\':
                stream.advance()
                string += escape_sequence(stream)
            else:
                string += stream.advance()
        if not stream.filled:
            raise Error(u"%s: Broken string literal" % start.repr())
        assert terminal == stream.advance()
        return Literal(start, stream.position, symtab[u'string'], string)
    elif stream.current in table:
        string = stream.advance()
        while stream.filled and string + stream.current in table:
            string += stream.advance()
        name = table[string]
        return Literal(start, stream.position, name, string)
    else:
        string = stream.advance()
        return Literal(start, stream.position, symtab[u'symbol'], string)

def escape_sequence(stream):
    if stream.current in escape_sequences:
        return chr(escape_sequences[stream.advance()])
    string = stream.advance()
    #\xhh The character whose numerical value is given by hh interpreted as a hexadecimal number
    if string == 'x':
        code = get_hex(stream) + get_hex(stream)
        if len(code) == 2:
            return chr(int(code, 16))
        return "\\" + string + code
    #\nnn The character whose numerical value is given by nnn interpreted as an octal number
    if string in "01234567":
        string += get_octal(stream) + get_octal(stream)
        if len(string) == 3:
            return chr(int(string, 8))
    return "\\" + string

def get_hex(stream):
    if stream.current in "0123456789ABCDEFabcdef":
        return stream.advance()
    return ""

def get_octal(stream):
    if stream.current in "01234567":
        return stream.advance()
    return ""

escape_sequences = {"a": 0x07, "b": 0x08, "f": 0x0C, "n": 0x0A, "r": 0x0D, "t": 0x09, "v": 0x0B, "\\": 0x5C, "'": 0x27, "\"": 0x22, "?": 0x3F}
