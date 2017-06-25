from lever_parser import Parser, Rule
import sys

# class Initiator
#     def __init__(self, init, extensions, keywords, symbols):
#         self.init = init
#         self.extensions = extensions
#         self.keywords = keywords
#         self.symbols = symbols
# 
#     def __call__(self, accept=None):
#         pos = tokenizer.Position(0, 1)
#         extensions = []
#         for item in self.extensions:
#             extensions.append( item[0](pos, item[1]...) )
#         parser = Parser(pos,
#             self, self.init(accept), extensions)
#         return parser
# 
#     def create_symtab(self):
#         return object();
#             string = self.symbols.get("string", None)
#             symbol = self.symbols.get("symbol", None)
#             hex = self.symbols.get("hex", None)
#             int = self.symbols.get("int", None)
#             float = self.symbols.get("float", None)
# 
#     def read_file(self, filename):
#         tokens = tokenizer.read_file(filename,
#             self.keywords,
#             self.create_symtab())
#         return self.read_tokens(tokens, filename)
# 
#     def read_string(self, string, source="<string>"):
#         tokens = tokenizer.read_string(string,
#             self.keywords,
#             self.create_symtab())
#         return self.read_tokens(tokens, source)
# 
#     def read_tokens(self, tokens, source="<string>"):
#         parser = self()
#         parser.source = source
#         for token in tokens:
#             parser.step(token.name, token, token.start, token.stop)
#         parser.finish()
#         return parser
# 
# class Parser
#     def __init__(self, pos, init, child, extensions):
#         self.pos = pos
#         self.init = init
#         self.child = child
#         self.extensions = extensions
#         self.source = "<unknown>"
# 
#     def step(self, term, token, start=None, stop=None):
#         for ext in self.extensions:
#             term = ext.step(self, term, token, start, stop)
#         if not self.child.expecting(term):
#             raise chartparser.SyntaxErrorExpected2(token,
#                 self.child.expect, start, self.source)
#         self.child.step(term, token, start, stop)
#         self.pos = stop
# 
#     accepted = property();
#         def get(self):
#             return self.child.accepted
# 
#     expect = property();
#         def get(self):
#             return self.child.expect
# 
#     def expecting(self, symbol):
#         return self.child.expecting(symbol)
# 
#     def finish(self):
#         for ext in self.extensions:
#             ext.finish(self)
#         if not self.child.accepted:
#             raise chartparser.SyntaxErrorExpected2(None,
#                 self.child.expect, self.pos, self.source, True)
# 
#     def traverse(self, postorder_cb, blank_cb=None, resolve_cb=None):
#         def g_postorder_cb(rule, tree, start, stop):
#             return rule.annotation.postorder(postorder_cb, tree, object();
#                 start = start
#                 stop = stop)
#         return self.child.traverse(
#             g_postorder_cb, blank_cb, resolve_cb)
# 
class AliasExtension(object):
    def __init__(self, pos, args, options):
        self.a = options.get("a", [])
        self.on = options.get("on", [])

    def step(self, i, term, token, start, stop):
        if (not i.expecting(term)) and term in self.on:
            for arg in self.a:
                if i.expecting(arg):
                    return arg
        return term
    
    def finish(self, i):
        pass
 
class IndentationExtension(object):
    def __init__(self, pos, args, options):
        self.indent = chartparser.IndentParser(pos, *args)
        self.can_close = set(options.get("can_close", []))

    def step(self, i, term, token, start, stop):
        self.indent.step(i.child, start, i.source)
        if not i.child.expecting(term) and term in self.can_close:
            self.indent.slip(i.child, start, i.source)
        return term

    def finish(self, i):
        if not self.indent.finish(i.child, i.pos, i.source):
            raise chartparser.SyntaxErrorExpected2("eof",
                i.child.expect, i.pos, i.source, True)

default_extensions = {
    "alias": AliasExtension,
    "indentation": IndentationExtension
}

def read_file_bare(filename):
    fn = lambda name, args, rest: globals()['post_'+name](args)
    out = language.parse.from_file(fn, [], filename)

    #Parser(language.keywords, language.grammar, language.grammar[0].lhs)

    # indent = chartparser.IndentParser(
    #     tokenizer.Position(0, 1),
    #     language.indent,
    #     language.dedent,
    #     language.newline)
    # parser = language.new_parser()
    # tokens = tokenizer.read_file(filename,
    #     language.keywords,
    #     language.symtab)
    # pos = tokenizer.Position(0, 1)
    # for token in tokens:
    #     term = token.name
    #     indent.step(parser, token.start, filename)
    #     if not parser.expecting(term) and term in language.can_close:
    #         indent.slip(parser, token.start, filename)
    #     if not parser.expecting(term) and term in language.keywords:
    #         term = language.symtab.symbol
    #     # TODO: move this inside the chartparser?
    #     if not parser.expecting(term):
    #         raise chartparser.SyntaxErrorExpected2(token.string,
    #             parser.expect, token.start, filename)
    #     parser.step(term, token, token.start, token.stop)
    #     pos = token.stop
    # # TODO: move this inside the chartparser?
    # indent.finish(parser, pos, filename)
    # if not parser.accepted:
    #     raise chartparser.SyntaxErrorExpected2("eof",
    #         parser.expect, token.stop, filename, True)

    # # TODO: move the 'loc' creation upwards into the chartparser
    # def run_action(name, args):
    #     return getattr(actions, name)(args)
    # def traverser(rule, tree, start, stop):
    #     loc = [start, stop]
    #     return rule.annotation.postorder(run_action, tree, loc)
    # out = parser.traverse(traverser)

    env = Object()
    env.constructives = set()
    env.templates     = {}
    env.template_memo = {}
    env.keywords = {}
    env.symbols  = {}
    env.rules    = []
    env.extensions = []
    for decl in out:
        decl(0, env)
    for decl in out:
        decl(1, env)
    return env
 
def build_grammar_language():
    # Used by the indentation parser
    indent = Nonterminal("indent")
    dedent = Nonterminal("dedent")
    newline = Nonterminal("newline")

    # Principal nonterminals
    file = Nonterminal('file')
    decl = Nonterminal('decl')
    option = Nonterminal('option')
    body = Nonterminal('body')
    prod = Nonterminal('prod')
    primitive = Nonterminal('primitive')
    expr = Nonterminal('expr')
    term = Nonterminal('term')
    prod_seq = Nonterminal('prod_seq')
    annotation      = Nonterminal('annotation')
    annotation_term = Nonterminal('annotation_term')

    # Helper nonterminals
    s_decl_nl = Nonterminal('0')
    s_symbol_c = Nonterminal('1')
    j_symbol_c = Nonterminal('2')
    j_option_nl = Nonterminal('3')
    o_kw_constructive = Nonterminal('4')
    s_primitive_c = Nonterminal('5')
    j_primitive_c = Nonterminal('6')
    j_prod_nl = Nonterminal('7')
    m_expr = Nonterminal('8')
    s_annotation_c = Nonterminal('9')
    j_annotation_c = Nonterminal('10')
    prod_seq_a = Nonterminal('11')
    prod_seq_b = Nonterminal('12')
    prod_seq_c = Nonterminal('13')

    # Terminals
    colon = Terminal(':')
    equal = Terminal('=')
    slash = Terminal('/')
    comma = Terminal(',')
    dot    = Terminal('.')
    dotdot = Terminal('..')
    lp = Terminal('(')
    rp = Terminal(')')
    lb = Terminal("[")
    rb = Terminal("]")
    lc = Terminal("{")
    rc = Terminal("}")
    star = Terminal("*")
    plus = Terminal("+")
    question = Terminal("?")
    percent  = Terminal("!")

    symbol = Terminal("symbol")
    string = Terminal("string")
    int    = Terminal("int")

    kw_use = Terminal('use')
    kw_append = Terminal('append')
    kw_concat = Terminal('concat')
    kw_constructive = Terminal('constructive')
    kw_terminal = Terminal('terminal')
    kw_None = Terminal('None')

    language = Object()
    language.keywords = { ":": colon,
        "=": equal, "/": slash,
        ",": comma, ".": dot, "..": dotdot,
        "(": lp, ")": rp, "[": lb, "]": rb, "{": lc, "}": rc,
        "*": star, "+": plus,
        "?": question, "%": percent,
        "use": kw_use,
        "append": kw_append,
        "concat": kw_concat,
        "constructive": kw_constructive,
        "terminal": kw_terminal,
        "None": kw_None }
    language.can_close = set([rp, lb, lc])
    language.indent = indent
    language.dedent = dedent
    language.newline = newline
    language.transitional = [
        kw_terminal, kw_None, kw_constructive,
        kw_use, kw_append ]
    language.symtab = Object()
        # symbol = symbol
        # int = int
        # string = string

    grammar = [
        Rule(file, [],      List()),
        Rule(file, [s_decl_nl], Get(0)),

        Rule(decl, [kw_use, symbol, lp, s_symbol_c, rp],         Label("use", [Get(1), Get(3), Null()])),
        Rule(decl, [kw_use, symbol, lp, s_symbol_c, rp,
            indent, j_option_nl, dedent],                        Label("use", [Get(1), Get(3), Get(6)])),
        Rule(decl, [o_kw_constructive, kw_terminal, s_symbol_c], Label("terminal", [Get(0), Get(2)])),
        Rule(decl, [symbol, lp, s_symbol_c, rp, colon, body],    Label("template", [Get(0), Get(2), Get(5)])),
        Rule(decl, [symbol, colon, body],                        Label("rule", [Get(0), Get(2)])),

        Rule(option, [symbol, equal, lb, s_primitive_c, rb], List([Get(0), Get(3)])),

        Rule(prod, [m_expr], Label("prod", [Get(0), Null()])),
        Rule(prod, [m_expr, slash, annotation], Label("prod", [Get(0), Get(2)])),
        Rule(prod, [m_expr, slash, symbol], Label("prod", [Get(0), Label("shorthand", [Get(2)])])),

        Rule(expr, [term], Get(0)),
        Rule(expr, [lp, prod_seq, rp, plus],     Label('plus', [Get(0)])),
        Rule(expr, [lp, prod_seq, rp, star],     Label('star', [Get(0)])),
        Rule(expr, [lp, prod_seq, rp, question], Label('opt', [Get(0)])),
        Rule(expr, [symbol, lp, prod_seq, rp], Label('expand', [Get(0), Get(2)])),

        Rule(prod_seq, [indent, prod_seq_b, dedent], Get(1)),
        Rule(prod_seq, [prod_seq_c], Get(0)),

        Rule(term, [term, plus],       Label('plus', [Get(0)])),
        Rule(term, [term, star],       Label('star', [Get(0)])),
        Rule(term, [term, question],   Label('opt', [Get(0)])),
        Rule(term, [symbol],           Label('symbol', [Get(0)])),
        Rule(term, [string],           Label('string', [Get(0)])),
        Rule(term, [lb, prod_seq, rb], Label('prod_set', [Get(1)])),

        Rule(annotation, [annotation_term],                        Get(0)),
        Rule(annotation, [annotation, kw_append, annotation_term], Label("append", [Get(0), Get(2)])),
        Rule(annotation, [annotation, kw_concat, annotation_term], Label("concat", [Get(0), Get(2)])),

        Rule(annotation_term, [lp, annotation, rp], Get(1)),
        Rule(annotation_term, [int],     Label("index", [Get(0)])),
        Rule(annotation_term, [dot],     Label("dot", [Get(0)])),
        Rule(annotation_term, [dotdot],  Label("dotdot", [Get(0)])),
        Rule(annotation_term, [kw_None], Label("a_None", [])),

        Rule(annotation_term, [symbol, lp, s_annotation_c, rp], Label("label", [Get(0), Get(2)])),
        Rule(annotation_term, [lb, s_annotation_c, rb],         Label("a_list", [Get(1)])),

        Rule(primitive, [symbol], Label('symbol', [Get(0)])),
        Rule(primitive, [string], Label('string', [Get(0)])),

        Rule(body, [prod],                      List([Get(0)])),
        Rule(body, [indent, j_prod_nl, dedent], Get(1)),

        Rule(s_decl_nl, [s_decl_nl, newline, decl], Append(Get(0), Get(2))),
        Rule(s_decl_nl, [decl],                     List([Get(0)])),

        Rule(o_kw_constructive, [], Null()),
        Rule(o_kw_constructive, [kw_constructive], Get(0)),

        Rule(s_symbol_c, [],           List()),
        Rule(s_symbol_c, [j_symbol_c], Get(0)),

        Rule(j_symbol_c, [symbol],                    List([Get(0)])),
        Rule(j_symbol_c, [j_symbol_c, comma, symbol], Append(Get(0), Get(2))),

        Rule(j_option_nl, [option],                       List([Get(0)])),
        Rule(j_option_nl, [j_option_nl, newline, option], Append(Get(0), Get(2))),

        Rule(s_primitive_c, [],              List()),
        Rule(s_primitive_c, [j_primitive_c], Get(0)),

        Rule(j_primitive_c, [primitive],                       List([Get(0)])),
        Rule(j_primitive_c, [j_primitive_c, comma, primitive], Append(Get(0), Get(2))),

        Rule(j_prod_nl, [prod], List([Get(0)])),
        Rule(j_prod_nl, [j_prod_nl, newline, prod], Append(Get(0), Get(2))),

        Rule(m_expr, [],             List()),
        Rule(m_expr, [m_expr, expr], Append(Get(0), Get(1))),

        Rule(prod_seq_b, [prod_seq_c], Get(0)),
        Rule(prod_seq_b, [prod_seq_b, newline, prod_seq_c], Concat(Get(0), Get(2))),

        Rule(prod_seq_c, [prod_seq_a],        Get(0)),
        Rule(prod_seq_c, [prod_seq_a, comma], Get(0)),

        Rule(prod_seq_a, [prod],                    List([Get(0)])),
        Rule(prod_seq_a, [prod_seq_a, comma, prod], Append(Get(0), Get(2))),

        Rule(s_annotation_c, [], List()),
        Rule(s_annotation_c, [j_annotation_c], Get(0)),

        Rule(j_annotation_c, [annotation],                        List([Get(0)])),
        Rule(j_annotation_c, [j_annotation_c, comma, annotation], Append(Get(0), Get(2))),
    ]

    #language.new_parser = chartparser.preprocess(
    #    grammar, file)
    
    language.parse = Parser(language.keywords, grammar, 'file')
    return language

def post_use(args):
    def _fn_(stage, env):
        if stage == 0:
            for arg in args[1]:
                sym = arg.value
                if sym not in env.symbols:
                    env.symbols[sym] = Terminal(sym)
                else:
                    assert isinstance(env.symbols[sym], Terminal)
                env.constructives.add(sym)
        if stage == 1:
            name = args[0].value
            argv = []
            for arg in args[1]:
                sym = arg.value
                argv.append(env.symbols[sym])
            options = {}
            for item in args[2]:
                key = item[0].value
                vals = []
                for val in item[1]:
                    vals.append( val(env, None).value )
                options[key] = vals
            env.extensions.append([name, argv, options])
    return _fn_

def post_rule(args):
    def _fn_ (stage, env):
        if stage == 0:
            sym = args[0].value
            if sym not in env.symbols:
                env.symbols[sym] = Nonterminal(sym)
            else:
                assert isinstance(env.symbols[sym], Nonterminal)
        if stage == 1:
            sub_env = {}
            lhs = env.symbols[args[0].value]
            for fn in args[1]:
                node = fn(env, sub_env)
                assert not node.is_sym
                env.rules.append( make_rule(lhs, node.value, node.annotation) )
    return _fn_
def post_template(args):
    def _fn_ (stage, env):
        if stage == 0:
            name = args[0].value
            argv = []
            for arg in args[1]:
                argv.append(arg.value)
            body = args[2]
            env.templates[name + "/" + str(argv.length)] = obj = Object()
            obj.argv = argv
            obj.body = body
    return _fn_
def post_terminal(args):
    def _fn_ (stage, env):
        if stage == 0:
            for token in args[1]:
                sym = token.value
                if sym not in env.symbols:
                    env.symbols[sym] = Terminal(sym)
                else:
                    assert isinstance(env.symbols[sym], Terminal)
                if args[0]:
                    env.constructives.add(sym)
    return _fn_
def post_prod(args):
    def _fn_(env, sub_env):
        rhs = []
        for fn in args[0]:
            rhs.append(fn(env, sub_env))
        return Prod(rhs, True, args[1])
    return _fn_
def post_shorthand(args):
    return Expr(expr_label, [args[0], [Expr(expr_dotdot, [])]])
def post_symbol(args):
    def _fn_(env, sub_env):
        sym = args[0].value
        if sym in sub_env:
            return sub_env[sym]
        else:
            return Sym(env.symbols[sym], sym not in env.constructives)
    return _fn_
def post_string(args):
    def _fn_(env, sub_env):
        kw = args[0].value
        if kw in env.keywords:
            sym = env.keywords[kw]
        else:
            sym = env.keywords[kw] = Terminal("'" + kw + "'")
        return Sym(sym, False)
    return _fn_
def post_plus(args):
    def _fn_(env, sub_env):
        arg = args[0](env, sub_env)
        key = ("+", arg)
        sym = env.template_memo.get(key)
        if not sym:
            lhs = Nonterminal(None)
            sym = env.template_memo[key] = Sym(lhs, True)
            env.rules.append(make_rule(lhs, [arg],
                Expr(expr_list, [Expr(expr_dot, [])])))
            env.rules.append(make_rule(lhs, [sym, arg],
                Expr(expr_append, [Expr(expr_dot, []), Expr(expr_dot, [])])))
        return sym
    return _fn_
def post_star(args):
    def _fn_(env, sub_env):
        arg = args[0](env, sub_env)
        key = ("*", arg)
        sym = env.template_memo.get(key)
        if not sym:
            lhs = Nonterminal(None)
            sym = env.template_memo[key] = Sym(lhs, True)
            env.rules.append(make_rule(lhs, [],
                Expr(expr_list, [])))
            env.rules.append(make_rule(lhs, [sym, arg],
                Expr(expr_append, [Expr(expr_index, [0]), Expr(expr_index, [1])])))
        return sym
    return _fn_
def post_opt(args):
    def _fn_(env, sub_env):
        arg = args[0](env, sub_env)
        key = ("?", arg)
        sym = env.template_memo.get(key)
        if not sym:
            lhs = Nonterminal(None)
            sym = env.template_memo[key] = Sym(lhs, True)
            env.rules.append(make_rule(lhs, [],
                Expr(expr_None, [])))
            env.rules.append(make_rule(lhs, [arg],
                Expr(expr_index, [0])))
        return sym
    return _fn_
def post_expand(args):
    def _fn_(env, sub_env):
        name = args[0].value
        argv = args[1]
        argl = []
        for arg in argv:
            a = arg(env, sub_env)
            # If we did not do this, the new production rule would
            # never trigger the memoization.
            while isinstance(a, Prod) and len(a.value) == 1 and a.annotation == None:
                a = a.value[0]
            # The simple cases of recursion can be handled without
            # problems.
            if isinstance(a, Arg):
                a = a.value
            argl.append(a)
        return expand_template(env, name, argl)
    return _fn_
def post_prod_set(args):
    def _fn_ (env, sub_env):
        if len(args[0]) == 1:
            return args[0][0](env, sub_env)
        lhs = Nonterminal(None)
        for fn in args[0]:
            node = fn(env, sub_env)
            assert not node.is_sym
            env.rules.append( make_rule(lhs, node.value, node.annotation) )
        return Sym(lhs, True)
    return _fn_
def post_index(args):
    index = int(args[0].value) - 1
    return Expr(expr_index, [index])
def post_dot(args):
    return Expr(expr_dot, args)
def post_dotdot(args):
    return Expr(expr_dotdot, args)
def post_label(args):
    return Expr(expr_label, args)
def post_a_list(args):
    return Expr(expr_list, args[0])
def post_append(args):
    return Expr(expr_append, args)
def post_concat(args):
    return Expr(expr_concat, args)
def post_a_None(args):
    return Expr(expr_None, args)

def expand_template(env, name, args):
    key = tuple([name, tuple(args)])
    sym = env.template_memo.get(key)
    if sym:
        return sym
    template_name = name + "/" + str(len(args))
    template = env.templates.get(template_name)
    if template:
        sub_env = {}
        # The overall idea in recognizing recursion this way is that
        # we start gathering Arg objects with same mark if something:
        # goes wrong.
        for i in range(len(args)):
            arg = Arg(args[i])
            assert arg.validate(template_name, i), ["infinite recursion at", template_name, i]
            sub_env[template.argv[i]] = arg
        lhs = Nonterminal(None)
        sym = env.template_memo[key] = Sym(lhs, True)
        for prod in template.body:
            node = prod(env, sub_env)
            env.rules.append(make_rule(lhs, node.value, node.annotation))
    elif name == "sep" and (len(args) == 2 or len(args) == 3):
        lhs = Nonterminal(None)
        sym = env.template_memo[key] = Sym(lhs, True)
        j_sym = expand_template(env, "join", [args[0], args[1]])
        env.rules.append(make_rule(lhs, [],
            Expr(expr_list, [])))
        env.rules.append(make_rule(lhs, [j_sym], Expr(expr_index, [0])))
        if len(args) == 3:
            c = args[2]
            env.rules.append(make_rule(lhs, [sym, c], Expr(expr_index, [0])))
    elif name == "join" and len(args) == 2:
        lhs = Nonterminal(None)
        sym = env.template_memo[key] = Sym(lhs, True)
        a = args[0]
        b = args[1]
        env.rules.append(make_rule(lhs, [a],
            Expr(expr_list, [Expr(expr_index, [0])])))
        env.rules.append(make_rule(lhs, [sym, b, a],
            Expr(expr_append, [Expr(expr_index, [0]), Expr(expr_index, [2])])))
    else:
        assert False, ["macro not found", template_name]
    return sym

def expr_index(stage, xenv, args):
    index = args[0]
    if stage == 0:
        xenv.args[index].gather = False
    return xenv.args[index].value

def expr_dot(stage, xenv, args):
    if stage == 0:
        if xenv.has_dotdot:
            xenv.last += 1
        else:
            xenv.first += 1
    elif stage == 1:
        return xenv.gathers.pop(0)

def expr_dotdot(stage, xenv, args):
    if stage == 0:
        assert not xenv.has_dotdot
        xenv.has_dotdot = True
    if stage == 1:
        a = []
        for i in range(xenv.dotdot_size):
            a.append(xenv.gathers.pop(0))
        return a

def expr_label(stage, xenv, args):
    if stage == 0:
        for item in args[1]:
            item(stage, xenv)
    elif stage == 1:
        name = args[0].value
        a = []
        for item in args[1]:
            v = item(stage, xenv)
            if isinstance(v, list):
                a.extend(v)
            else:
                a.append(v)
        return Label(name, a)

def expr_list(stage, xenv, args):
    if stage == 0:
        for item in args:
            item(stage, xenv)
    elif stage == 1:
        a = []
        for item in args:
            v = item(stage, xenv)
            if isinstance(v, list):
                a.extend(v)
            else:
                a.append(v)
        return List(a)

def expr_append(stage, xenv, args):
    if stage == 0:
        for item in args:
            item(stage, xenv)
    elif stage == 1:
        return Append(args[0](stage, xenv), args[1](stage, xenv))

def expr_concat(stage, xenv, args):
    if stage == 0:
        for item in args:
            item(stage, xenv)
    elif stage == 1:
        return Concat(args[0](stage, xenv), args[1](stage, xenv))

def expr_None(stage, xenv, args):
    if stage == 1:
        return Null()

class Arg:
    def __init__(self, value):
        self.is_sym = True
        self.value = value
        self.gather = True
        self.marks = value.get_marks(set())
    
    def __hash__(self):
        return hash(self.value)

    def get_marks(self, marks):
        marks.update(self.marks)
        return marks

    def validate(self, *key):
        if key in self.marks:
            return False
        self.marks.add(key)
        return True
 
class Sym:
    def __init__(self, value, gather):
        self.is_sym = True
        self.value = value
        self.gather = gather

    def get_marks(self, marks):
        return marks
    
    def __hash__(self):
        return hash(self.value)

    def __eq__(a, b):
        if isinstance(b, Sym):
            return a.value == b.value
        return False
 
class Prod:
    def __init__(self, value, gather, annotation):
        self.is_sym = False
        self.value = value
        self.gather = gather
        self.annotation = annotation

    def get_marks(self, marks):
        for a in self.value:
            marks = a.get_marks(marks)
        return marks

    def __hash__(self):
        return hash((tuple(self.value), self.annotation))

    def __eq__(a, b):
        if isinstance(b, Prod):
            return a.value == b.value and a.annotation == b.annotation
        return False

class Expr:
    def __init__(self, fn, args):
        self.fn = fn
        self.args = args

    def __hash__(self):
        return hash((self.fn, tuple(self.args)))

    def __call__(self, stage, xenv):
        return self.fn(stage, xenv, self.args)

    def __eq__(a, b):
        if isinstance(b, Expr):
            return a.fn == b.fn and a.args == b.args
        return False

    def __repr__(self):
        return "Expr({}, {})".format(self.fn.__name__, self.args)

# # Accepts a list of structures with fields:
# # .is_sym - whether it's a symbol or a list of fields like this.
# # .value
# # .gather - whether the value is gathered or not.
# # .annotation - function building the annotation, unless it is_sym
# # This is done in a single step, because computing the indices for 'Get':
# # in an expression is easy that way.
def make_rule(lhs, rhs, fn):
    #assert isinstance(lhs, Nonterminal)
    syms = []
    def build_rhs(rhs, fn):
        args = []
        for node in rhs:
            gather = node.gather
            while isinstance(node, Arg):
                node = node.value
            if node.is_sym:
                syms.append(node.value)
                v = Object()
                v.value = Get(len(syms) - 1)
                v.gather = gather
                args.append(v)
            else:
                v = Object()
                v.value = build_rhs(node.value, node.annotation)
                v.gather = gather
                args.append(v)
        return extract_annotation(fn, args, [lhs, syms])
    return Rule(lhs, syms, build_rhs(rhs, fn))

def extract_annotation(expr, args, syms):
    if expr:
        xenv = Object()
        xenv.args = args
        xenv.gathers = []
        xenv.first = 0
        xenv.last = 0
        xenv.has_dotdot = False
        xenv.dotdot_size = 0
        expr(0, xenv)
        # The indices potentially change the gather values, so that's why
        for arg in args:
            if arg.gather:
                xenv.gathers.append(arg.value)
        xenv.dotdot_size = len(xenv.gathers) - xenv.first - xenv.last
        assert xenv.dotdot_size >= 0, [xenv.dotdot_size, expr, syms]
        return expr(1, xenv)
    else:
        a = []
        for arg in args:
            if arg.gather:
                a.append(arg.value)
        # At default handling, if nothing can be gathered:
        # yet the rhs is not empty, we pick all.
        # This is rare otherwise and allows the string
        # gather without explicit marks everywhere.
        if len(a) == 0 and len(args) > 0:
            for arg in args:
                a.append(arg.value)
        if len(a) == 0:
            return Null()
        if len(a) == 1:
            return a[0]
        return List(a)

# These are the elements that are built from the annotations
# in the grammar file. They are structured to make the
# interpretation of the parse tree easy.
class Annotation(object):
    def __call__(self, namespace, args, rest):
        return self.postorder(namespace, args, rest)

class Label(Annotation):
    def __init__(self, name, args):
        assert isinstance(name, str)
        self.name = name
        self.args = args

    def __repr__(self):
        a = []
        for arg in self.args:
            a.append( repr(arg) )
        return self.name + "(" + ", ".join(a) + ")"

    def postorder(self, fn, args, loc):
        a = []
        for x in self.args:
            a.append( x.postorder(fn, args, loc) )
        return fn(self.name, a, loc)

class List(Annotation):
    def __init__(self, args=[]):
        self.args = args

    def __repr__(self):
        a = []
        for arg in self.args:
            a.append( repr(arg) )
        return "[" + ", ".join(a) + "]"

    def postorder(self, fn, args, loc):
        a = []
        for x in self.args:
            a.append( x.postorder(fn, args, loc) )
        return a

class Get(Annotation):
    def __init__(self, index):
        self.index = index

    def __repr__(self):
        return "Get(" + str(self.index) + ")"

    def postorder(self, fn, args, loc):
        return args[self.index]

class Append(Annotation):
    def __init__(self, sequence, value):
        self.sequence = sequence
        self.value = value

    def __repr__(self):
        return ("Append(" + repr(self.sequence) + ", " +
            repr(self.value) + ")")

    def postorder(self, fn, args, loc):
        sequence = self.sequence.postorder(fn, args, loc)
        sequence.append( self.value.postorder(fn, args, loc) )
        return sequence

class Concat(Annotation):
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return ("Concat(" + repr(self.left) + ", " +
            repr(self.right) + ")")

    def postorder(self, fn, args, loc):
        left = self.left.postorder(fn, args, loc)
        right = self.right.postorder(fn, args, loc)
        return left + right

class Null(Annotation):
    def __repr__(self):
        return "Null()"

    def postorder(self, fn, args, loc):
        return None

class Object(object):
    def __repr__(self):
        return "Object({})".format(" ".join("."+n for n in dir(self) if not n.startswith('_')))

label_index = 0

Terminal = lambda x: x
def Nonterminal(y):
    global label_index
    if y is None:
        label_index += 1
        return "__{}__".format(label_index)
    return y

language = build_grammar_language()


def load(filename, extension_env=default_extensions):
    env = read_file_bare(filename)
    # for use in env.extensions
    #     print(use[0], use[1], use[2].items()...)
    # for rule in env.rules:
    #     print(rule)
    first_symbol = Nonterminal(None)
    for rule in env.rules:
        if not rule.lhs.startswith('_'):
            first_symbol = rule.lhs
            break

    for keyword in list(env.keywords):
        for m in default_smear(keyword):
            env.keywords[m] = "'" + m + "'"
    ## initiator = chartparser.preprocess(env.rules, env.rules[0].lhs)
    ## extensions = []
    ## for extension in env.extensions:
    ##     name = extension[0]
    ##     if name not in extension_env:
    ##         raise Error("Extension " + name + " not present")
    ##     ext = extension_env[name]
    ##     extensions.append([ext, extension[1 :]])
    ## return Initiator(initiator, extensions, env.keywords, env.symbols)
    return Parser(env.keywords, env.rules, first_symbol)

# Smear the keywords so they 
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
