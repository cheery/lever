from stream import CStream
from tokenizer import L2
from data import Expr, Literal
import space

table = {
    '(': 'lp', ')': 'rp',
    '[': 'lb', ']': 'rb',
    '{': 'lc', '}': 'rc',
    'and': 'and', 'or': 'or', 'not': 'not',
    '=': 'let', ':=': 'set',
    '<': 'chain',
    '>': 'chain',
    '<=': 'chain',
    '>=': 'chain',
    '==': 'chain',
    '!=': 'chain',
    '^': 'op', '&': 'op', '<<': 'op',
    '>>': 'op', '!': 'op', '*': 'op',
    '/': 'op', '%': 'op', '+': 'op',
    '-': 'op', '|': 'op',
    ':': 'symbol',
    '.': 'dot'}
binops = {
    '|': 10,
    '^': 10,
    '&': 20,
    '<<': 30, '>>': 40,
    '+': 40, '-': 40,
    '*': 50, '/': 50, '%': 50,
}
right_binding = []
prefixes = {
    '~': 90,
    '-': 90,
    '+': 90,
}
postfixes = {
    '!': 100,
}

def read(source):
    exps = []
    ts = L2(CStream(source), table)
    while ts.filled:
        if ts.position.col != 0:
            raise space.Error(ts.first.start.str() + ": layout error")
        exps.append(toplevel(ts, 0))
    return exps

def toplevel(ts, col):
    head = expression(ts)
    if head.dcf is not None and ts.filled:
        if head.stop.lno == ts.position.lno:
            head.dcf.capture = [toplevel(ts, col)]
        elif ts.position.col > col:
            head.dcf.capture = exps = []
            scol = ts.position.col
            while ts.filled and ts.position.col == scol:
                exp = toplevel(ts, scol)
                exps.append(exp)
                while ts.filled and ts.position.lno == exp.stop.lno and ts.position.col > scol:
                    exps.append(toplevel(ts, scol))
    return head

def expressions(ts):
    exps = []
    while ts.filled:
        if match_some(ts.first, ['rp', 'rb', 'rc']):
            break
        exps.append(expression(ts))
    return exps

def expression(ts):
    left = expression_and(ts)
    if match(ts.first, 'or'):
        op = ts.advance()
        op.name = 'symbol'
        right = expression(ts)
        return Expr(left.start, right.stop, 'form', [op, left, right])
    return left

def expression_and(ts):
    left = expression_chain(ts)
    if match(ts.first, 'and'):
        op = ts.advance()
        op.name = 'symbol'
        right = expression_and(ts)
        return Expr(left.start, right.stop, 'form', [op, left, right])
    return left

def expression_chain(ts):
    left = expression_bare(ts, 0)
    if match(ts.first, 'chain'):
        exps = [left]
        while match(ts.first, 'chain'):
            op = ts.advance()
            op.name = 'symbol'
            exps.append(op)
            exps.append(expression_bare(ts, 0))
        left = Expr(exps[0].start, exps[len(exps)-1].stop, 'chain', exps)
    return left

def expression_bare(ts, rbp):
    if on_prefix(ts):
        op = ts.advance()
        op.name = 'symbol'
        exp = expression_bare(ts, prefixes[op.value])
        left = Expr(op.start, exp.stop, 'prefix', [op, exp])
    else:
        left = terminal(ts)
    while ts.filled:
        if match(ts.first, 'dot'):
            dot = ts.advance()
            symbol = ts.advance()
            if not match(symbol, 'symbol'):
                raise space.Error(symbol.start.str() + ": expected symbol")
            left = Expr(left.start, symbol.stop, 'attr', [left, symbol])
        elif match(ts.first, 'lb') and left.stop.eq(ts.first.start):
            lb = ts.advance()
            exps = expressions(ts)
            if not match(ts.first, 'rb'):
                raise space.Error(lb.start.str() + ": [ truncates at " + ts.position.str())
            rb = ts.advance()
            left = Expr(left.start, rb.stop, 'index', [left] + exps)
        elif match_some(ts.first, ['let', 'set']):
            let = ts.advance()
            exp = expression(ts)
            left = Expr(left.start, exp.stop, let.name, [left, exp])
        elif match(ts.first, 'op') and match(ts.second, 'let') and ts.first.value in binops:
            aug = ts.advance()
            aug.name = 'symbol'
            let = ts.advance()
            exp = expression(ts)
            left = Expr(left.start, exp.stop, 'aug', [aug, left, exp])
        else:
            break
    while ts.filled:
        if on_binop(left, ts) and rbp < binops.get(ts.first.value, 0):
            op = ts.advance()
            op.name = 'symbol'
            lbp = binops.get(op.value, 0)
            right = expression_bare(ts, lbp - (ts.first.value in right_binding))
            left = Expr(left.start, right.stop, 'form', [op, left, right])
        elif on_postfix(left, ts) and rbp < postfixes.get(ts.first.value, 0):
            op = ts.advance()
            op.name = 'symbol'
            lbp = postfixes.get(op.value, 0)
            left = Expr(left.start, op.stop, 'postfix', [op, left])
        else:
            break
    return left

def terminal(ts):
    if match_some(ts.first, ['symbol', 'string', 'int', 'float']):
        return ts.advance()
    elif match(ts.first, 'lp'):
        lp = ts.advance()
        exps = expressions(ts)
        if not match(ts.first, 'rp'):
            raise space.Error(lp.start.str() + ": form truncates at " + ts.position.str())
        rp = ts.advance()
        exp = Expr(lp.start, rp.stop, 'form', exps)
        exp.dcf = exp
        return exp
    elif match(ts.first, 'lb'):
        lb = ts.advance()
        exps = expressions(ts)
        if not match(ts.first, 'rb'):
            raise space.Error(lb.start.str() + ": list truncates at " + ts.position.str())
        rb = ts.advance()
        exp = Expr(lb.start, rb.stop, 'list', exps)
        exp.dcf = exp
        return exp
    elif match(ts.first, 'lc'):
        lc = ts.advance()
        if match(ts.second, 'rc'):
            exp = ts.advance()
        else:
            exp = expression(ts)
        rc = ts.advance()
        return exp
    elif match(ts.first, 'not'):
        op = ts.advance()
        op.name = 'symbol'
        exp = expression_chain(ts)
        return Expr(op.start, exp.stop, 'form', [op, exp])
    if ts.filled:
        raise space.Error(ts.position.str() + ": expected term, got " + ts.first.value)
    raise space.Error(ts.position.str() + ": expected term, got eof")

def match_some(t, names):
    return t is not None and t.name in names

def match(t, name):
    return t is not None and t.name == name

def on_prefix(ts):
    if match(ts.first, 'op') and ts.second is not None:
        return ts.first.stop.eq(ts.second.start)
    return False

def on_binop(left, ts):
    if match(ts.first, 'op') and ts.second is not None:
        l = left.stop.eq(ts.first.start)
        r = ts.first.stop.eq(ts.second.start)
        return l == r
    return False

def on_postfix(left, ts):
    if match(ts.first, 'op'):
        l = left.stop.eq(ts.first.start)
        r = ts.second is not None and ts.first.stop.eq(ts.second.start)
        return l and not r
    return False
