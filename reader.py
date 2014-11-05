from object import List, String, Symbol, Integer

class WontParse(Exception):
    pass

class PartialParse(WontParse):
    pass

class Stream:
    def __init__(self, source):
        self.source = source
        self.index = 0
        self.empty = self.index >= len(self.source)
        if self.empty:
            self.character = ' '
        else:
            self.character = self.source[self.index]

    def advance(self):
        character = self.character
        self.index += 1
        self.empty = self.index >= len(self.source)
        if self.empty:
            self.character = ' '
        else:
            self.character = self.source[self.index]
        return character

def read_file(path):
    fd = open(path)
    lst = read_source(fd.read())
    fd.close()
    return lst

def read_source(source):
    stream = Stream(source)
    lst = []
    while not stream.empty:
        if stream.character == ')':
            raise WontParse("excess right parenthesis")
        node = read(stream)
        if node is not None:
            lst.append(node)
    return List(lst)

def read(stream):
    while stream.character.isspace():
        if stream.empty:
            return None
        stream.advance()
    if stream.character == '(':
        stream.advance()
        lst = []
        while stream.character != ')':
            if stream.empty:
                raise PartialParse("right parenthesis missing")
            node = read(stream)
            if node is not None:
                lst.append(node)
        stream.advance()
        return List(lst)
    if issym(stream.character):
        string = stream.advance()
        if string == '-' and isnum(stream.character):
            return readNum(string, stream)
        while issym(stream.character) or isnum(stream.character):
            string += stream.advance()
        return Symbol(string)
    if isnum(stream.character):
        return readNum('', stream)
    if stream.character == '"':
        stream.advance()
        string = ''
        slurp = False
        while stream.character != '"' or slurp:
            if stream.empty:
                raise PartialParse("string terminator missing")
            if slurp:
                slurp = False
            elif stream.character == '\\':
                slurp = True
            string += stream.advance()
        stream.advance()
        return String(string)
    if stream.character == ')':
        return None
    raise WontParse("unknown character: " + str(ord(stream.character)))

def readNum(prefix, stream):
    num = stream.advance()
    if num == '0' and stream.character == 'x':
        stream.advance()
        num = prefix + num
        while ishex(stream.character):
            num += stream.advance()
        return Integer(int(num, 16))
    num = prefix + num
    while isnum(stream.character):
        num += stream.advance()
    return Integer(int(num))

def issym(ch):
    return ch.isalpha() or ch in "!%&*+-./:;<=>?@[]^_|"

def ishex(ch):
    return ch.isdigit() or ch in "abcdefABCDEF"

def isnum(ch):
    return ch.isdigit()
