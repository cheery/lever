"""
    The structures exposed outside
    reader module.
"""
class Position(object):
    def __init__(self, col, lno):
        self.col = col
        self.lno = lno

    def repr(self):
        return u"%d:%d" % (self.lno, self.col)

    def eq(self, other):
        return self.col == other.col and self.lno == other.lno

    def ne(self, other):
        return self.col != other.col or self.lno != other.lno

    def __repr__(self):
        return "{}:{}".format(self.lno, self.col)

class Node(object):
    dcf = None # Stands for 'default capturing form'

class Literal(Node):
    def __init__(self, start, stop, name, value):
        self.start = start
        self.stop = stop
        self.name = name
        self.value = value
        self.lsp = False
        self.rsp = False

    def repr(self):
        return u"%s %s %s %s" % (
            self.start.repr(),
            self.stop.repr(),
            self.name,
            self.value)

    def __repr__(self):
        return "{0.name};{0.value!r}".format(self)

class Expr(Node):
    capture = [] # The capture block
    def __init__(self, start, stop, name, exps):
        self.start = start
        self.stop = stop
        self.name = name
        self.exps = exps
        for exp in exps:
            if exp.dcf is not None:
                self.dcf = exp.dcf

    def repr(self):
        t = u"%s %s %s" % (self.start.repr(), self.stop.repr(), self.name)
        for exp in self.exps:
            t += u"\n  " + indent(exp.repr())
        if len(self.capture) > 0:
            t += u"\n  capture"
        for exp in self.capture:
            t += u"\n  " + indent(exp.repr())
        return t

def indent(s):
    o = u""
    for c in s:
        if c == u'\n':
            o += u'\n  '
        else:
            o += c
    return o
