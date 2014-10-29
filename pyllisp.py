import sys, os
from object import Object, List, String, Symbol, Integer, BuiltinFunction, true, false, null
from reader import read_file
from rpython.config.translationoption import get_combined_translation_config
from rpython.rlib.rtimer import read_timestamp

config = get_combined_translation_config(translating=True)

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

class Closure(Object):
    def __init__(self, env, expr):
        self.env = env
        self.expr = expr
        self.arglist = []
        assert isinstance(expr[1], List)
        for symbol in expr[1]:
            assert isinstance(symbol, Symbol)
            self.arglist.append(symbol.string)

    def invoke(self, argv):
        env = Environment(self.env, self.env.global_scope)
        c = len(self.arglist)
        b = min(c, len(argv))
        for i in range(0, b):
            env.namespace[self.arglist[i]] = argv[i]
        for i in range(b, c):
            env.namespace[self.arglist[i]] = null
        retval = null
        for i in range(2, len(self.expr)):
            interpret(env, self.expr[i])
        return retval

    def repr(self):
        return self.expr.repr()

def pyl_print(argv):
    space = ''
    for arg in argv:
        if isinstance(arg, String):
            string = arg.string
        else:
            string = arg.repr()
        os.write(1, space + string)
        space = ' '
    os.write(1, '\n')
    return null

global_scope = {
    "print": BuiltinFunction(pyl_print, "print"),
    "true": true,
    "false": false,
    "null": null,
}

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

def is_false(flag):
    return flag is null or flag is false

macros = {
    'cond': cond_macro,
    'while': while_macro,
    '=': letvar_macro,
    ':=': setvar_macro,
    'func': func_macro,
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
        return env.lookup(expr.string)
    else:
        return expr

def entry_point(argv):
    print "[STAMP BEGIN] "
    now = read_timestamp()
    if len(argv) <= 1:
        raise Exception("too few arguments")
    lst = read_file(argv[1])
    assert isinstance(lst, List)
    env = Environment(None, global_scope)
    for expr in lst:
        interpret(env, expr)
    delta = read_timestamp() - now
    print "[STAMP NOW] " + str(delta)
    return 0

def target(*args):
    return entry_point, None

if __name__=='__main__':
    sys.exit(entry_point(sys.argv))
