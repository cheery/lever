"""
    The structures exposed outside
    reader module.
"""
class Position(object):
    def __init__(self, col, lno):
        self.col = col
        self.lno = lno

    def __repr__(self):
        return "{0.lno}:{0.col}".format(self)
    
    def eq(self, other):
        return self.col == other.col and self.lno == other.lno

    def ne(self, other):
        return self.col != other.col or self.lno != other.lno

    def str(self):
        return str(self.lno) + ":" + str(self.col)

class Node(object):
    dcf = None # Stands for 'default capturing form'

class Literal(Node):
    def __init__(self, start, stop, name, value):
        self.start = start
        self.stop = stop
        self.name = name
        self.value = value

    def __repr__(self):
        return "{0.start} {0.stop} {0.name} {0.value!r}".format(self)

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

    def __repr__(self):
        a = ''.join('\n  ' + repr(exp).replace('\n', '\n  ') for exp in self.exps)
        if self.capture:
            a += '\n  capture' + ''.join('\n  ' + repr(exp).replace('\n', '\n  ') for exp in self.capture)
        return "{0.start} {0.stop} {0.name} {1}".format(self, a)
