import grammarlang
parser = grammarlang.load_from_string({}, grammarlang.__doc__)
for i in range(50):
    env = grammarlang.Env({}, {})
    grammar = parser(grammarlang.__dict__, env, grammarlang.__doc__)
    parser = grammarlang.Parser(env.symboltab, grammar, grammar[0].lhs)
