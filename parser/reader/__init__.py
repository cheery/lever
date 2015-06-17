from stream import CStream
from tokenizer import L2
from data import Expr, Literal, Position
#import space

#table = {
#    u'(': u'lp', u')': u'rp',
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
#binops = {
#    u'|': 10,
#    u'^': 10,
#    u'&': 20,
#    u'<<': 30, u'>>': 40,
#    u'++': 40, u'+': 40, u'-': 40,
#    u'*': 50, u'/': 50, u'%': 50,
#}
#right_binding = []
#prefixes = {
#    u'~': 90,
#    u'-': 90,
#    u'+': 90,
#}
#postfixes = {
#    u'!': 100,
#}
#
#def read(source):
#    exps = []
#    ts = L2(CStream(source), table)
#    while ts.filled:
#        if ts.position.col != 0:
#            raise space.Error(u"%s: layout error" % ts.first.start.repr())
#        exps.append(toplevel(ts, 0))
#    return exps
#
#def toplevel(ts, col):
#    head = expression(ts)
#    if head.dcf is not None and ts.filled:
#        if head.stop.lno == ts.position.lno:
#            head.dcf.capture = [toplevel(ts, col)]
#        elif ts.position.col > col:
#            head.dcf.capture = exps = []
#            scol = ts.position.col
#            while ts.filled and ts.position.col == scol:
#                exp = toplevel(ts, scol)
#                exps.append(exp)
#                while ts.filled and ts.position.lno == exp.stop.lno and ts.position.col > scol:
#                    exps.append(toplevel(ts, scol))
#    return head
#
#def expressions(ts):
#    exps = []
#    while ts.filled:
#        if match_some(ts.first, [u'rp', u'rb', u'rc']):
#            break
#        exps.append(expression(ts))
#    return exps
#
#def expression(ts):
#    left = expression_and(ts)
#    if match(ts.first, u'or'):
#        op = ts.advance()
#        op.name = u'symbol'
#        right = expression(ts)
#        return Expr(left.start, right.stop, u'form', [op, left, right])
#    return left
#
#def expression_and(ts):
#    left = expression_chain(ts)
#    if match(ts.first, u'and'):
#        op = ts.advance()
#        op.name = u'symbol'
#        right = expression_and(ts)
#        return Expr(left.start, right.stop, u'form', [op, left, right])
#    return left
#
#def expression_chain(ts):
#    left = expression_bare(ts, 0)
#    if match(ts.first, u'chain'):
#        exps = [left]
#        while match(ts.first, u'chain'):
#            op = ts.advance()
#            op.name = u'symbol'
#            exps.append(op)
#            exps.append(expression_bare(ts, 0))
#        left = Expr(exps[0].start, exps[len(exps)-1].stop, u'chain', exps)
#    return left
#
#def expression_bare(ts, rbp):
#    if on_prefix(ts):
#        op = ts.advance()
#        exp = expression_bare(ts, prefixes[op.value])
#        op.name = u'symbol'
#        op.value = op.value+u'expr'
#        left = Expr(op.start, exp.stop, u'form', [op, exp])
#    else:
#        left = terminal(ts)
#    while ts.filled:
#        if match(ts.first, u'dot'):
#            dot = ts.advance()
#            symbol = ts.advance()
#            if not match(symbol, u'symbol'):
#                raise space.Error(u"%s: expected symbol" % symbol.start.repr())
#            left = Expr(left.start, symbol.stop, u'attr', [left, symbol])
#        elif match(ts.first, u'lb') and left.stop.eq(ts.first.start):
#            lb = ts.advance()
#            exps = expressions(ts)
#            if not match(ts.first, u'rb'):
#                raise space.Error(u"%s: [] truncates at %s" % (lb.start.repr(), ts.position.repr()))
#            rb = ts.advance()
#            left = Expr(left.start, rb.stop, u'index', [left] + exps)
#        elif match_some(ts.first, [u'let', u'set']):
#            let = ts.advance()
#            exp = expression(ts)
#            left = Expr(left.start, exp.stop, let.name, [left, exp])
#        elif match(ts.first, u'op') and match(ts.second, u'let') and ts.first.value in binops:
#            aug = ts.advance()
#            aug.name = u'symbol'
#            let = ts.advance()
#            exp = expression(ts)
#            left = Expr(left.start, exp.stop, u'aug', [aug, left, exp])
#        else:
#            break
#    while ts.filled:
#        if on_binop(left, ts) and rbp < binops.get(ts.first.value, 0):
#            op = ts.advance()
#            op.name = u'symbol'
#            lbp = binops.get(op.value, 0)
#            right = expression_bare(ts, lbp - (ts.first.value in right_binding))
#            left = Expr(left.start, right.stop, u'form', [op, left, right])
#        elif on_postfix(left, ts) and rbp < postfixes.get(ts.first.value, 0):
#            op = ts.advance()
#            op.name = u'symbol'
#            lbp = postfixes.get(op.value, 0)
#            op.value = u'expr'+op.value
#            left = Expr(left.start, op.stop, u'form', [op, left])
#        else:
#            break
#    return left
#
#def terminal(ts):
#    if match_some(ts.first, [u'symbol', u'string', u'int', u'hex', u'float']):
#        return ts.advance()
#    elif match(ts.first, u'lp'):
#        lp = ts.advance()
#        exps = expressions(ts)
#        if not match(ts.first, u'rp'):
#            raise space.Error(u"%s: form truncates at %s" % (lp.start.repr(), ts.position.repr()))
#        rp = ts.advance()
#        exp = Expr(lp.start, rp.stop, u'form', exps)
#        exp.dcf = exp
#        return exp
#    elif match(ts.first, u'lb'):
#        lb = ts.advance()
#        exps = expressions(ts)
#        if not match(ts.first, u'rb'):
#            raise space.Error(u"%s: list truncates at %s" % (lb.start.repr(), ts.position.repr()))
#        rb = ts.advance()
#        exp = Expr(lb.start, rb.stop, u'list', exps)
#        exp.dcf = exp
#        return exp
#    elif match(ts.first, u'lc'):
#        lc = ts.advance()
#        if match(ts.second, u'rc'):
#            exp = ts.advance()
#            exp.name = u'symbol'
#        else:
#            exp = expression(ts)
#        rc = ts.advance()
#        return exp
#    elif match(ts.first, u'not'):
#        op = ts.advance()
#        op.name = u'symbol'
#        exp = expression_chain(ts)
#        return Expr(op.start, exp.stop, u'form', [op, exp])
#    if ts.filled:
#        raise space.Error(u"%s: expected term, got %s" % (ts.position.repr(), ts.first.value))
#    raise space.Error(u"%s: expected term, got eof" % ts.position.repr())
#
#def match_some(t, names):
#    return t is not None and t.name in names
#
#def match(t, name):
#    return t is not None and t.name == name
#
#def on_prefix(ts):
#    if match(ts.first, u'op') and ts.second is not None:
#        return ts.first.stop.eq(ts.second.start)
#    return False
#
#def on_binop(left, ts):
#    if match(ts.first, u'op') and ts.second is not None:
#        l = left.stop.eq(ts.first.start)
#        r = ts.first.stop.eq(ts.second.start)
#        return l == r
#    return False
#
#def on_postfix(left, ts):
#    if match(ts.first, u'op'):
#        l = left.stop.eq(ts.first.start)
#        r = ts.second is not None and ts.first.stop.eq(ts.second.start)
#        return l and not r
#    return False
