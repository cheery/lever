from earley import Rule, print_result
from reader import CStream, L2, Literal
import earley
import sys

class Parser(object):
    def __init__(self, symboltab, grammar, accept, debug=False):
        self.init, self.nullable = earley.simulate(grammar, accept, debug)
        self.symboltab = symboltab
        self.debug = debug

    def from_file(self, namespace, env, path):
        with open(path) as fd:
            return self(namespace, env, fd.read())

    def __call__(self, namespace, env, source):
        parser = earley.Parser(self.init, self.nullable)
        stream = L2(CStream(source), self.symboltab)
        indent_stack = []
        indent = 0 if stream.first is None else stream.first.start.col
        line = 0 if stream.first is None else stream.first.start.lno
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
            expect = parser.expect
            token = stream.advance()
            parser.step(token)
            if len(parser.chart[-1]) == 0:
                if self.debug: print_result(parser)
                trail = format_expect(expect)
                raise Exception("{0.lno}:{0.col}: parse error at {1.name} {1.value!r}\n{2}"
                    .format(token.start, token, trail))
        while 'dedent' in parser.expect:
            stop = token.stop
            parser.step(Literal(stop, stop, 'dedent', ''))
        if not parser.accept:
            if self.debug: print_result(parser)
            trail = format_expect(parser.expect)
            raise Exception("{0.lno}:{0.col}: parse error at end of file\n{1}"
                .format(stream.stream, trail))
        if self.debug: print_result(parser)
        return traverse(parser, parser.root, 0, len(parser.input), namespace, env)

def format_expect(expect):
    trail = "expected end of file"
    if len(expect) > 0:
        trail = "expected some of: {}".format(', '.join(map(str, expect)))
    return trail

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
