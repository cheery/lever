def main():
    grammar = [
        Rule('S', ['A', 'A', 'A', 'A']),
        Rule('A', ['E']),
        Rule('A', ['a']),
        Rule('E', []),
    ]
    init = simulate(grammar, 'S')
    parser = Parser(init)

    for token in "a":
        parser.step(token)
    print_result(parser)

def main():
    grammar = [
        Rule('S', ['a']),
        #Rule('S', ['S', 'a']),
        Rule('S', ['a', 'S']),
    ]
    init = simulate(grammar, 'S')
    parser = Parser(init)

    for token in "aaaaa":
        parser.step(token)
    print_result(parser)

def main():
    grammar = [
        Rule('S', ['a']),
        #Rule('S', ['S', 'a']),
        Rule('S', ['a', '+', 'S']),
    ]
    init = simulate(grammar, 'S')
    parser = Parser(init)

    for token in "a+a+a+a+a+a+a+a+a+a+a+a+a":
        parser.step(token)
    print_result(parser)

def main():
    grammar = [
        Rule('S', ['N']),
        Rule('S', ['S', '+', 'N']),
        Rule('N', ['a']),
        Rule('N', ['N', '*', 'a']),
    ]
    init = simulate(grammar, 'S')
    parser = Parser(init)

    for token in "a+a+a*a":
        parser.step(token)
    print_result(parser)

table = {
    u'(': u'lp', u')': u'rp',
    u'[': u'lb', u']': u'rb',
    u'{': u'lc', u'}': u'rc',
    u'and': u'and', u'or': u'or', u'not': u'not',
    u'=': u'let', u':=': u'set',
    u'<': u'chain',
    u'>': u'chain',
    u'<=': u'chain',
    u'>=': u'chain',
    u'==': u'chain',
    u'!=': u'chain',
    u'^': u'op', u'&': u'op', u'<<': u'op',
    u'>>': u'op', u'!': u'op', u'*': u'op',
    u'/': u'op', u'%': u'op', u'+': u'op',
    u'-': u'op', u'|': u'op', u'++': u'op',
    u':': u'symbol',
    u'.': u'dot'}
binops = {
    u'|': 10,
    u'^': 10,
    u'&': 20,
    u'<<': 30, u'>>': 40,
    u'++': 40, u'+': 40, u'-': 40,
    u'*': 50, u'/': 50, u'%': 50,
}
right_binding = []
prefixes = {
    u'~': 90,
    u'-': 90,
    u'+': 90,
}
postfixes = {
    u'!': 100,
}

def main():
    from reader import CStream, L2
    source = """
    hello wolf
    hello
        lollelstein
    hello hello
    """

    grammar = [
        Rule('file', ['expr']),
        Rule('file', ['file', 'newline', 'expr']),
        Rule('expr', ['symbol']),
        Rule('expr', ['expr', 'symbol']),
    ]

    stream = L2(CStream(source), table)
    parser = Parser(simulate(grammar, 'file', debug=True))
    output = []

    base_stack = []
    base = stream.first.start
    while stream.filled:
        while stream.first.start.col < base.col and 'dedent' in parser.expect:
            parser.step('dedent')
            output.append(None)
            base = base_stack.pop()
        if stream.first.start.col == base.col and 'newline' in parser.expect:
            parser.step('newline')
            output.append(None)
        if stream.first.start.col > base.col and 'indent' in parser.expect:
            parser.step('indent')
            output.append(None)
            base_stack.append(base)
            base = stream.first.start

        if stream.first.name not in parser.expect:
            assert False, ('expected', parser.expect)
        token = stream.advance()
        parser.step(token.name)
        output.append(token)

    print_result(parser)

