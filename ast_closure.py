from object import Object, List, Symbol, is_false

def cond_macro(env, exprs):
    retval = null
    for i in range(1, len(exprs)):
        block = exprs[i]
        head = block[0]
        if not (isinstance(head, Symbol) and head.string == 'else'):
            if is_false(interpret(env, head)):
                continue
        for i in range(1, len(block)):
            retval = interpret(env, block[i])
        break
    return retval

def while_macro(env, exprs):
    assert len(exprs) > 2
    retval = null
    cond = exprs[1]
    while not is_false(interpret(env, cond)):
        for i in range(2, len(exprs)):
            retval = interpret(env, exprs[i])
    return retval

def letvar_macro(env, exprs):
    assert len(exprs) == 3
    lhs, rhs = exprs[1], exprs[2]
    assert isinstance(lhs, Symbol)
    retval = env.namespace[lhs.string] = interpret(env, rhs)
    return retval

def setvar_macro(env, exprs):
    assert len(exprs) == 3
    lhs, rhs = exprs[1], exprs[2]
    assert isinstance(lhs, Symbol)
    dst = env
    while dst is not None:
        if lhs.string in dst.namespace:
            retval = dst.namespace[lhs.string] = interpret(env, rhs)
            return retval
        dst = dst.parent
    raise Exception("no such variable: " + lhs.string)

def func_macro(env, exprs):
    assert len(exprs) > 2
    return Closure(env, exprs)

def return_macro(env, exprs):
    assert len(exprs) == 2
    raise Return(interpret(env, exprs[1]))

macros = {
    'cond': cond_macro,
    'while': while_macro,
    '=': letvar_macro,
    ':=': setvar_macro,
    'func': func_macro,
    'return': return_macro,
}

def interpret(env, expr):
    if isinstance(expr, List):
        if len(expr) == 0:
            raise Exception("cannot evaluate ()")
        if isinstance(expr[0], Symbol) and expr[0].string in macros:
            macro = macros[expr[0].string]
            return macro(env, expr)
        callee = interpret(env, expr[0])
        args = []
        for i in range(1, len(expr)):
            args.append(interpret(env, expr[i]))
        return callee.invoke(args)
    elif isinstance(expr, Symbol):
        if expr.string.startswith('.'):
            N = len(expr.string)
            if expr.string.endswith('='):
                return SetAccessor(expr.string[1:max(1, N-1)])
            if expr.string.endswith('!'):
                return CallAccessor(expr.string[1:max(1, N-1)])
            return GetAccessor(expr.string[1:N])
        blok = expr.string.split('.')
        retval = env.lookup(blok[0])
        for i in range(1, len(blok)):
            retval = retval.getattr(blok[i])
        return retval
        #return env.lookup(expr.string)
    else:
        return expr

class GetAccessor(Object):
    def __init__(self, name):
        self.name = name

    def invoke(self, argv):
        assert len(argv) == 1
        return argv[0].getattr(self.name)

    def repr(self):
        return "." + self.name

class SetAccessor(Object):
    def __init__(self, name):
        self.name = name

    def invoke(self, argv):
        assert len(argv) == 2
        return argv[0].setattr(self.name, argv[1])

    def repr(self):
        return "." + self.name + '='

class CallAccessor(Object):
    def __init__(self, name):
        self.name = name

    def invoke(self, argv):
        N = len(argv)
        assert N >= 1
        return argv[0].callattr(self.name, argv[1:N])

    def repr(self):
        return "." + self.name + '!'

class Environment:
    def __init__(self, parent, global_scope):
        self.parent = parent
        self.namespace = {}
        self.global_scope = global_scope

    def lookup(self, name):
        if name in self.namespace:
            return self.namespace[name]
        if name in self.global_scope:
            return self.global_scope[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise Exception(name + " not in scope")

class Return(Exception):
    def __init__(self, retval):
        self.retval = retval

class Closure(Object):
    def __init__(self, env, expr):
        self.env = env
        self.expr = expr
        self.arglist = []
        self.vararg = None
        assert isinstance(expr[1], List)
        for symbol in expr[1]:
            assert isinstance(symbol, Symbol)
            if symbol.string.endswith('...'):
                self.vararg = symbol.string[0:max(0, len(symbol.string)-3)]
            else:
                self.arglist.append(symbol.string)

    def invoke(self, argv):
        env = Environment(self.env, self.env.global_scope)
        c = len(self.arglist)
        b = min(c, len(argv))
        for i in range(0, b):
            env.namespace[self.arglist[i]] = argv[i]
        for i in range(b, c):
            env.namespace[self.arglist[i]] = null
        if self.vararg is not None:
            varg = []
            for i in range(c, len(argv)):
                varg.append(argv[i])
            env.namespace[self.vararg] = List(varg)
        try:
            for i in range(2, len(self.expr)):
                interpret(env, self.expr[i])
        except Return as ret:
            return ret.retval
        return null

    def repr(self):
        return self.expr.repr()

