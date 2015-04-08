"""
    Tokenizer with two-token lookahead stream.
"""
from stream import CStream
from data import Literal
import space

class L2(object):
    def __init__(self, stream, table):
        self.stream = stream
        self.table = table
        self.first = next_token(self.stream, self.table)
        self.second = next_token(self.stream, self.table)
    
    def advance(self):
        t = self.first
        self.first = self.second
        self.second = next_token(self.stream, self.table)
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
    if stream.current == '#':
        while stream.filled and stream.current != '\n':
            stream.advance()
        return next_token(stream, table)
    start = stream.position
    if stream.is_sym():
        string = stream.advance()
        while stream.is_sym() or stream.is_digit():
            string += stream.advance()
        name = table.get(string, 'symbol')
        return Literal(start, stream.position, name, string)
    elif stream.is_digit():
        string = stream.advance()
        if string == '0' and stream.filled and stream.current == 'x':
            string += stream.advance()
            while stream.is_hex():
                string += stream.advance()
            return Literal(start, stream.position, 'hex', string)
        while stream.is_digit():
            string += stream.advance()
        if stream.filled and stream.current == '.':
            string += stream.advance()
            while stream.is_digit():
                string += stream.advance()
            return Literal(start, stream.position, 'float', string)
        return Literal(start, stream.position, 'int', string)
    elif stream.current in ('"', "'"):
        terminal = stream.advance()
        string = ""
        while stream.filled and stream.current != terminal:
            if stream.current == '\\':
                stream.advance()
            string += stream.advance()
        if not stream.filled:
            raise space.Error(str(start.lno) + ": Broken string literal")
        assert terminal == stream.advance()
        return Literal(start, stream.position, 'string', string)
    elif stream.current in table:
        string = stream.advance()
        while stream.filled and string + stream.current in table:
            string += stream.advance()
        name = table[string]
        return Literal(start, stream.position, name, string)
    else:
        string = stream.advance()
        return Literal(start, stream.position, 'symbol', string)
