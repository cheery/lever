from lever_parser import Parser, Rule
import sys

symboltab = {
        '=': 'equals',
        '=>': 'arrow',
        ',': 'comma',
        '{': 'lc',
        '}': 'rc',
        '[': 'lb',
        ']': 'rb',
        '%': 'skip',
        '^': 'grab',
        '@': 'at'
}

class Grab(object):
    def __init__(self, index):
        self.index = index
    
    def __call__(self, actions, args, argl):
        return args[self.index]

class Command(object):
    def __init__(self, name, args):
        self.name = name
        self.args = args
    
    def __call__(self, actions, args, argl):
        action = actions['post_' + self.name]
        argv = list(argl)
        for arg in self.args:
            argv.append(arg(actions, args, argl))
        return action(*argv)

class Group(object):
    def __init__(self, args):
        self.args = args

    def __call__(self, actions, args, argl):
        group = []
        for arg in self.args:
            group.append(arg(actions, args, argl))
        return group

def blank(actions, args, argl):
    return None

def build_language():
    nonterminal = lambda x: x
    terminal = lambda x: x
    keyword = lambda x: symboltab[x]

    file = nonterminal("file")
    rule = nonterminal("rule")
    production = nonterminal("production")
    productions = nonterminal("productions")
    inline_productions = nonterminal("inline_productions")
    term = nonterminal("term")
    block = nonterminal("block")

    indent = terminal("indent")
    dedent = terminal("dedent")
    newline = terminal("newline")
    string = terminal("string")
    symbol = terminal("symbol")

    arrow = keyword("=>")
    comma = keyword(",")
    lc = keyword("{")
    rc = keyword("}")
    lb = keyword("[")
    rb = keyword("]")
    at = keyword("@")
    skip = keyword("%")
    grab = keyword("^")

    grammar = [
        Rule(file, [rule],
            Grab(0)),
        Rule(file, [file, newline, rule],
            Command("extend", [Grab(0), Grab(2)])),
        Rule(rule, [symbol, arrow, production],
            Command("rule", [Grab(0), Command("first", [Grab(2)])])),
        Rule(rule, [symbol, arrow, block],
            Command("rule", [Grab(0), Grab(2)])),
        Rule(rule, [symbol, arrow, lb, inline_productions, rb],
            Command("rule", [Grab(0), Grab(3)])),
        Rule(block, [indent, productions, dedent],
            Grab(1)),
        Rule(productions, [lb, inline_productions, rb],
            Grab(1)),
        Rule(productions, [production],
            Command("first", [Grab(0)])),
        Rule(productions, [productions, newline, production],
            Command("append", [Grab(0), Grab(2)])),
        Rule(production, [production, term],
            Command("append", [Grab(0), Grab(1)])),
        Rule(production, [term],
            Command("first", [Grab(0)])),
        Rule(production, [lc, production, rc],
            Grab(1)),
        Rule(production, [lc, rc],
            Command("empty", [])),
        Rule(inline_productions, [production],
            Command("first", [Command("force_grab", [Grab(0)])])),
        Rule(inline_productions, [inline_productions, comma, production],
            Command("append", [Grab(0), Command("force_grab", [Grab(2)])])),
        Rule(term, [skip, at, symbol],
            Command("skip", [Command("terminal", [Grab(2)])])),
        Rule(term, [grab, at, symbol],
            Command("grab", [Command("terminal", [Grab(2)])])),
        Rule(term, [skip, symbol],
            Command("skip", [Command("symbol", [Grab(1)])])),
        Rule(term, [grab, symbol],
            Command("grab", [Command("symbol", [Grab(1)])])),
        Rule(term, [skip, string],
            Command("skip", [Command("string", [Grab(1)])])),
        Rule(term, [grab, string],
            Command("grab", [Command("string", [Grab(1)])])),
        Rule(term, [string],
            Command("skip", [Command("string", [Grab(0)])])),
        Rule(term, [symbol],
            Command("grab", [Command("symbol", [Grab(0)])])),
        Rule(term, [at, symbol],
            Command("grab", [Command("terminal", [Grab(1)])])),
        Rule(term, [symbol, lc, rc],
            Command("command", [Grab(0)])),
        Rule(term, [symbol, lc, production, rc],
            Command("command", [Grab(0), Grab(2)])),
    ]
    return grammar

grammar = build_language()

def post_command(table, loc, symbol, arg=[]):
    return {
        "name": "command",
        "command": symbol.value,
        "arg": arg}

def post_skip(table, loc, arg):
    return {
        "name": "skip",
        "arg": arg}

def post_grab(table, loc, arg):
    return {
        "name": "grab",
        "arg": arg}

def post_terminal(table, loc, token):
    return table.terminal(token.value)

def post_symbol(table, loc, token):
    return table.nonterminal(token.value)

def post_string(table, loc, token):
    return table.keyword(token.value)

def post_rule(table, loc, symbol, productions):
    lhs = table.nonterminal(symbol.value)
    result = []
    for production in productions:
        result.append(make_rule(lhs, production))
    return result

def post_force_grab(table, loc, productions):
    for cell in productions:
        if cell["name"] == "skip":
            cell["name"] = "grab"
    return productions

def post_append(env, loc, seq, item):
    seq.append(item)
    return seq

def post_extend(env, loc, seq, item):
    seq.extend(item)
    return seq

def post_first(env, loc, item):
    return [item]

def make_rule(lhs, production):
    rhs = []
    annotation = make_command(rhs, None, production)
    return Rule(lhs, rhs, annotation)

def make_command(rhs, command, production):
    clist = []
    for prod in production:
        if prod["name"] == 'skip':
            rhs.append(prod["arg"])
        elif prod["name"] == 'grab':
            clist.append(Grab(len(rhs)))
            rhs.append(prod["arg"])
        elif prod["name"] == 'command':
            clist.append(make_command(rhs, prod["command"], prod["arg"]))
        else:
            raise Error(repr(prod["name"]))
    if command:
        return Command(command, clist)
    elif len(clist) == 0:
        return blank
    elif len(clist) == 1:
        return clist[0]
    else:
        return Group(clist)
# 
# def post_single_rule(env, loc, lhs, (rhs, attribute, mapping)):
#     return [Rule(lhs.value, rhs, attribute, mapping)]
# 
# def post_multiple_rule(env, loc, lhs, block):
#     seq = []
#     for rhs, attribute, mapping in block:
#         seq.append(Rule(lhs.value, rhs, attribute, mapping))
#     return seq
# 
# def post_implicit_pass_rule(env, loc, items):
#     attribute = 'pass' if len(items) == 1 else 'tuple'
#     return [cell for name, cell in items], attribute, None
# 
# def post_labelled_rule(env, loc, label, items):
#     return [cell for name, cell in items], label.value, None
# 
# def post_labelled_mapped_rule(env, loc, label, mapping, items):
#     k = [name for name, cell in items]
#     mapping = [k.index(name) for name in mapping]
#     return [cell for name, cell in items], label.value, mapping
# 
# def post_named_item(env, loc, name, (_, cell)):
#     return name.value, cell
# 
# def post_symbolic_item(env, loc, symbol):
#     return symbol.value, symbol.value
# 
# def post_special(env, loc, name, keyword):
#     symboltab = env.symboltab
#     name = name.value
#     keyword = keyword.value
#     assert keyword not in symboltab or symboltab[keyword] == 'symbol' or symboltab[keyword] == name
#     symboltab[keyword] = name
#     while len(keyword) > 1:
#         keyword = keyword[:len(keyword)-1]
#         symboltab[keyword] = symboltab.get(keyword, 'symbol')
#     return name, name
# 
# def post_call(env, loc, name, arguments):
#     return env.functions[name.value](*arguments)
# 
# def post_append_arg_item(env, loc, seq, item):
#     seq.append(item)
#     return seq
# 
# def post_append_arg_str(env, loc, seq, token):
#     seq.append(token.value)
#     return seq
# 
# def post_append_arg_int(env, loc, seq, token):
#     seq.append(int(token.value))
#     return seq
# 
# def post_nothing(env, loc):
#     return None
# 
# def post_pass(env, loc, arg):
#     return arg

class SymbolTable(object):
    def __init__(self):
        self.terminals = {}
        self.nonterminals = {}
        self.keywords = {}

    def terminal(self, name):
        try:
            return self.terminals[name]
        except KeyError as _:
            self.terminals[name] = s = name
            return s

    def nonterminal(self, name):
        try:
            return self.nonterminals[name]
        except KeyError as _:
            self.nonterminals[name] = s = "<" + name + ">"
            return s

    def keyword(self, name):
        if name not in self.keywords:
            for keyword in default_smear(name):
                self.keywords[keyword] = "'" + keyword + "'"
        return self.terminal("'" + name + "'")

def default_smear(keyword):
    for ch in keyword:
        if ch.isalpha():
            return [keyword]
    result = []
    prefix = []
    for ch in keyword:
        prefix.append(ch)
        result.append("".join(prefix))
    return result

parse = Parser(symboltab, grammar, 'file')

def load(functions, path):
    table = SymbolTable()
    #for t in ["indent", "dedent", "newline", "string", "symbol", "int", "hex", "float"]:
    #    table.nonterminals[t] = table.terminal(t)
    grammar = parse.from_file(globals(), [table], path)
    assert len(grammar) > 0, "empty grammar"
    return Parser(table.keywords, grammar, grammar[0].lhs)

def load_from_string(functions, string):
    table = SymbolTable()
    for t in ["indent", "dedent", "newline", "string", "symbol", "int", "hex", "float"]:
        table.nonterminals[t] = table.terminal(t)
    grammar = parse(globals(), [table], string)
    assert len(grammar) > 0, "empty grammar"
    return Parser(table.keywords, grammar, grammar[0].lhs)
