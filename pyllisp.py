import sys, os
from object import List, String, Symbol, Integer, BuiltinFunction, true, false, null
from reader import read_file
from rpython.config.translationoption import get_combined_translation_config
from rpython.rlib.rtimer import read_timestamp

config = get_combined_translation_config(translating=True)

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

env = {
    "print": BuiltinFunction(pyl_print, "print"),
    "true": true,
    "false": false,
    "null": null,
}

def interpret(env, expr):
    if isinstance(expr, List):
        if len(expr) == 0:
            raise Exception("cannot evaluate ()")
        callee = interpret(env, expr[0])
        args = []
        for i in range(1, len(expr)):
            args.append(interpret(env, expr[i]))
        return callee.invoke(args)
    elif isinstance(expr, Symbol):
        if expr.string not in env:
            raise Exception(expr.string + " not in scope")
        return env[expr.string]
    else:
        return expr

def entry_point(argv):
    print "[STAMP BEGIN] "
    now = read_timestamp()
    if len(argv) <= 1:
        raise Exception("too few arguments")
    lst = read_file(argv[1])
    assert isinstance(lst, List)
    for expr in lst:
        interpret(env, expr)

    delta = read_timestamp() - now
    print "[STAMP NOW] " + str(delta)
    return 0

def target(*args):
    return entry_point, None

if __name__=='__main__':
    sys.exit(entry_point(sys.argv))
