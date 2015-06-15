from earley import Rule
from reader import CStream, L2
import earley
import sys

table = {
    u'(': u'leftparen', u')': u'rightparen',
    u'+': u'plus'}
#    u'[': u'lb', u']': u'rb',
#    u'{': u'lc', u'}': u'rc',
#    u'and': u'and', u'or': u'or', u'not': u'not',
#    u'=': u'let', u':=': u'set',
#    u'<': u'chain',
#    u'>': u'chain',
#    u'<=': u'chain',
#    u'>=': u'chain',
#    u'==': u'chain',
#    u'!=': u'chain',
#    u'^': u'op', u'&': u'op', u'<<': u'op',
#    u'>>': u'op', u'!': u'op', u'*': u'op',
#    u'/': u'op', u'%': u'op', u'+': u'op',
#    u'-': u'op', u'|': u'op', u'++': u'op',
#    u':': u'symbol',
#    u'.': u'dot'}

def early(token):
    return token.value == 'earley' and token.lsp == token.rsp == False

grammar = [
    #Rule('file', []), # XXX: fix a bug, if you use empty rule instead, it won't parse
                       # XXX: verify that the bug fix works.
    Rule('file', ['term']), 
    Rule('file', ['term', 'file']),
    Rule('term', ['symbol']),
    #Rule('term', ['leftparen', early, 'rightparen']),
]
init, nullable = earley.simulate(grammar, 'file', True)

source = open(sys.argv[1]).read()
stream = L2(CStream(source), table)
parser = earley.Parser(init, nullable)

while stream.filled:
    token = stream.advance()
    parser.step(token)

earley.print_result(parser)

def traverse(parser, rule, start, stop):
    midresults = list(parser.chains(rule.rhs, start, stop))
    for midresult in midresults:
        print start, stop, rule.lhs, midresult
    if len(midresults) > 1:
        raise Exception("ambiguity at {}:{}".format(start, stop))
    for midresult in midresults:
        for nonleaf, srule, sstart, sstop in midresult:
            if nonleaf:
                traverse(parser, srule, sstart, sstop)

for rule in parser.roots:
    traverse(parser, rule, 0, len(parser.input))
