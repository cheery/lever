from earley import Rule
from reader import CStream, L2, Literal
import earley
import sys
import pprint

table = {
    u'(': u'leftparen', u')': u'rightparen',
    u'+': u'plus',
    u'if': u'if',
    u'elif': u'elif',
    u'else': u'else',
#    u'[': u'lb', u']': u'rb',
#    u'{': u'lc', u'}': u'rc',
#    u'and': u'and', u'or': u'or', u'not': u'not',
    u'=': u'let', u':=': u'set',
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
    u'.': u'dot'}

grammar = [
    Rule('file', ['statement'],
        "new_list"),
    Rule('file', ['file', 'newline', 'statement'],
        "append", [0, 2]),
    Rule('statement', ['clause'],
        "through"),
    Rule('statement', ['statement', 'if', 'clause'],
        "inline_if", [2, 0]),
    Rule('statement', ['exprs', 'indent', 'file', 'dedent'],
        "call_with_block", [0, 2]),
    Rule('statement', ['cond'],
        "through"),
    Rule('cond', ['cond_chain', 'otherwise'],
        "cond"),
    Rule('otherwise', [], "nothing"),
    Rule('otherwise', ['newline', 'else', 'indent', 'file', 'dedent'],
        "through", [3]),
    Rule('cond_chain', ['if', 'clause', 'indent', 'file', 'dedent'],
        'tuple_list', [1, 3]),
    Rule('cond_chain', ['cond_chain', 'newline', 'elif', 'clause', 'indent', 'file', 'dedent'],
        'tuple_append', [0, 3, 5]),
    Rule('statement', ['symbol', 'let', 'statement'],
        "let", [0, 2]),
    Rule('statement', ['symbol', 'set', 'statement'],
        "set", [0, 2]),
    Rule('clause', ['expr'],
        "through"),
    Rule('clause', ['expr', 'exprs'],
        "call"),
    Rule('exprs', ['expr'],
        "new_list"),
    Rule('exprs', ['exprs', 'expr'],
        "append"),
    Rule('expr', ['postfix'],
        "through"),
    Rule('postfix', ['postfix', 'dot', 'symbol'],
        "getattr", [0, 2]),
    Rule('postfix', ['term'],
        "through"),
    Rule('term', ["symbol"],
        "through"),
    Rule('term', ["int"],
        "through"),
    Rule('term', ["float"],
        "through"),
    Rule('term', ["string"],
        "through"),
    Rule('term', ['leftparen', 'expr', 'rightparen'],
        "through", [1]),
]

def post_new_list(env, *args):
    return list(args)

def post_append(env, lst, item):
    lst.append(item)
    return lst

def post_through(env, arg):
    return arg

def post_call_with_block(env, exprs, block):
    return 'call', exprs + block

def post_call(env, callee, exprs):
    return 'call', [callee] + exprs

def post_getattr(env, expr, name):
    return 'getattr', expr, name

def post_let(env, lhs, rhs):
    return 'let', lhs, rhs

def post_set(env, lhs, rhs):
    return 'set', lhs, rhs

def post_inline_if(env, cond, expr):
    return 'if', cond, expr, None

def post_cond(env, conds, otherwise):
    return 'cond', conds, otherwise

def post_tuple_list(env, *args):
    return [args]

def post_tuple_append(env, lst, *args):
    lst.append(args)
    return lst

def post_nothing(env, *args):
    return None

source = open(sys.argv[1]).read()
stream = L2(CStream(source), table)
parser = earley.parser(grammar, 'file')

indent_stack = []
indent = stream.first.start.col
line = stream.first.start.lno
while stream.filled:
    if line < stream.first.start.lno:
        while stream.first.start.col < indent and 'dedent' in parser.expect:
                start = stream.first.start
                parser.step(Literal(start, start, 'dedent', ''))
                indent = indent_stack.pop()
        assert stream.first.start.col >= indent
        if stream.first.start.col == indent and 'newline' in parser.expect:
            start = stream.first.start
            parser.step(Literal(start, start, 'newline', ''))
        if stream.first.start.col > indent and 'indent' in parser.expect:
            start = stream.first.start
            parser.step(Literal(start, start, 'indent', ''))
            indent_stack.append(indent)
            indent = stream.first.start.col
        line = stream.first.start.lno

    token = stream.advance()
    parser.step(token)
    if len(parser.chart[-1]) == 0:
        raise Exception("parse error at: {}".format(token))
while 'dedent' in parser.expect:
    stop = token.stop
    parser.step(Literal(stop, stop, 'dedent', ''))

#earley.print_result(parser)

def traverse(parser, rule, start, stop, namespace, arg):
    mapping = rule.mapping
    if rule.lhs is Ellipsis:
        pre = None
        post = lambda arg, node: node
    else:
        assert rule.attribute is not None, rule
        pre = namespace.get("pre_{}".format(rule.attribute))
        post = namespace["post_{}".format(rule.attribute)]
    if callable(pre):
        arg = pre(arg)
    midresults = list(parser.chains(rule.rhs, start, stop))
    if len(midresults) == 0:
        raise Exception("parser bug at {}:{}".format(start, stop))
    if len(midresults) > 1:
        for midresult in midresults:
            print start, stop, rule.lhs, midresult
        raise Exception("ambiguity at {}:{}".format(start, stop))
    args = []
    for nonleaf, rule, start, stop in midresults[0]:
        if nonleaf:
            args.append(traverse(parser, rule, start, stop, namespace, arg))
        else:
            args.append(rule)
    return post(arg, *(args[index] for index in mapping))

arg = None
result = traverse(parser, parser.root, 0, len(parser.input), globals(), arg)
pprint.pprint(result)
