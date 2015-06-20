class SpacingCheck(object):
    def __init__(self, symbol):
        self.symbol = symbol

    def __eq__(self, other):
        return (type(self) is type(other) and
            self.symbol == other.symbol)

class BinarySpacing(SpacingCheck):
    def __call__(self, token):
        return token.name == self.symbol and token.lsp == token.rsp

    def __repr__(self):
        return 'binary {}'.format(self.symbol)

class PrefixSpacing(SpacingCheck):
    def __call__(self, token):
        return token.name == self.symbol and token.lsp and not token.rsp

    def __repr__(self):
        return 'prefix {}'.format(self.symbol)

class PostfixSpacing(SpacingCheck):
    def __call__(self, token):
        return token.name == self.symbol and token.rsp and not token.lsp

    def __repr__(self):
        return 'postfix {}'.format(self.symbol)

class TightSpacing(SpacingCheck):
    def __call__(self, token):
        return token.name == self.symbol and not token.lsp

    def __repr__(self):
        return 'tight {}'.format(self.symbol)

class LooseSpacing(SpacingCheck):
    def __call__(self, token):
        return token.name == self.symbol and token.lsp

    def __repr__(self):
        return 'loose {}'.format(self.symbol)

def spacing_func(cls):
    def _func_((key, sym)):
        return key, cls(sym)
    return _func_

functions = {
    'binary_spacing': spacing_func(BinarySpacing),
    'prefix_spacing': spacing_func(PrefixSpacing),
    'postfix_spacing': spacing_func(PostfixSpacing),
    'tight': spacing_func(TightSpacing),
    'loose': spacing_func(LooseSpacing)}
