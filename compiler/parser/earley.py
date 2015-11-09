from collections import OrderedDict, defaultdict

class Parser(object):
    def __init__(self, init, nullable):
        self.input = []
        self.chart = [OrderedDict()]
        self.chart[0][(init, 0)] = None
        self.chart[0][(init.goto[None], 0)] = None
        self.expect = set(init.goto) | set(init.goto[None].goto)
        self.accept = init.accept or init.goto[None].accept
        self.nullable = nullable

    def step(self, token):
        i = len(self.chart)
        current = OrderedDict()
        self.chart.append(current)
        self.input.append(token)
        # scan
        for state, parent in self.chart[i-1]:
            try:
                k = state.goto[token.name]
                current[(k, parent)] = None
            except KeyError as ke:
                pass
            for condition, k in state.conditions:
                if condition(token):
                    current[(k, parent)] = None
        # complete
        accept = False
        expect = set()
        #found = set()
        for state, parent in current:
            expect.update(state.goto)
            accept |= (parent == 0 and state.accept)
            #if parent == i: # XXX: Find out why I inserted this originally.
            #    continue
            for rule in state.completed:
                for pstate, pparent in self.chart[parent]:
                    # XXX: Fix chain constructor for this.
                    #if rule in found:
                    #    pstate, pparent = self.try_reduction_path(pstate, pparent)
                    try:
                        k = pstate.goto[rule.lhs]
                        current[(k, pparent)] = None
                    except KeyError as ke:
                        pass
                #found.add(rule)
            # predict
            try:
                current[(state.goto[None], i)] = None
            except KeyError as ke:
                pass
        self.accept = accept
        self.expect = expect

    def try_reduction_path(self, state, parent):
        gparent = parent
        for pstate, pparent in self.chart[parent]:
            if pstate == state and gparent > pparent:
                gparent = pparent
        if gparent != parent:
            return self.try_reduction_path(state, gparent)
        return state, parent

    def find(self, name, stop):
        out = set()
        for state, parent in self.chart[stop]:
            for rule in state.completed:
                if rule.lhs == name:
                    out.add((parent, rule))
        return out

    def chains(self, rhs, start, stop, index=None):
        if index is None:
            index = len(rhs) - 1
        if index < 0 and start == stop:
            yield []
        elif index == 0:
            if start+1 == stop and match(rhs[index], self.input[start]):
                yield [(False, self.input[start], start, stop)]
            for middle, rule in self.find(rhs[index], stop):
                if middle == start and (self.is_nullable(rule) or middle < stop):
                    yield [(True, rule, start, stop)]
        else:
            if match(rhs[index], self.input[stop-1]):
                for result in self.chains(rhs, start, stop-1, index-1):
                    yield result + [(False, self.input[stop-1], stop-1, stop)]
            for middle, rule in self.find(rhs[index], stop):
                # The second condition is to prevent non-nullable rules to present themselves
                # as a solution to empty slot. (similar line also on the above)
                if middle >= start and (self.is_nullable(rule) or middle < stop):
                    for result in self.chains(rhs, start, middle, index-1):
                        yield result + [(True, rule, middle, stop)]

    @property
    def root(self):
        for start, rule in self.find(Ellipsis, len(self.input)):
            if start == 0:
                return rule
        return None

    @property
    def roots(self):
        for start, rule in self.find(Ellipsis, len(self.input)):
            if start == 0:
                assert len(rule.rhs) == 1
                for start, rule in self.find(rule.rhs[0], len(self.input)):
                    if start == 0:
                        yield rule

    # Used by chains -implementation, if not used
    # later on design, I may remove it as result of simulate()
    def is_nullable(self, rule):
        return all(name in self.nullable for name in rule.rhs)

class Rule(object):
    def __init__(self, lhs, rhs, attribute=None, mapping=None):
        self.lhs = lhs
        self.rhs = rhs
        self.attribute = attribute
        self.mapping = tuple(range(len(rhs))) if mapping is None else mapping

    def __repr__(self):
        return "{} -> {}".format(self.lhs, ' '.join(map(str, self.rhs)))

class Item(object):
    def __init__(self, rule, index):
        self.rule = rule
        self.index = index

    def __eq__(self, other):
        return type(self) == type(other) and self.rule is other.rule and self.index is other.index

    def __hash__(self):
        return hash((type(self), self.rule, self.index))

    def __repr__(self):
        rule = self.rule
        rhs = ' '.join(map(str, rule.rhs[:self.index] + ["."] + rule.rhs[self.index:]))
        return "{} -> {}".format(rule.lhs, rhs)

class State(object):
    def __init__(self, index, completed, accept):
        self.index = index
        self.goto = {}
        self.conditions = set()
        self.completed = completed
        self.accept = accept

    def __repr__(self):
        return "State({})".format(self.index)

def parser(grammar, target, debug=False):
    init, nullable = simulate(grammar, target)
    return Parser(init, nullable)

def simulate(grammar, target, debug=False):
    nullable = set()
    changed = True
    while changed:
        m = len(nullable)
        for rule in grammar:
            if all(x in nullable for x in rule.rhs):
                nullable.add(rule.lhs)
        n = len(nullable)
        changed = m < n

    itemsets_out = OrderedDict()
    itemsets = OrderedDict()

    initset = frozenset([Item(Rule(Ellipsis, [target]), 0)])
    itemsets[initset] = None

    for itemset, is_nul in itemsets.iteritems():
        accept = False
        completed = set()
        current = OrderedDict()
        for item in itemset:
            current[item] = None
        edges = defaultdict(set)
        for item in current:
            if item.index < len(item.rule.rhs):
                symbol = item.rule.rhs[item.index]
                for rule in grammar:
                    if rule.lhs == symbol:
                        if is_nul:
                            current[Item(rule, 0)] = None
                        else:
                            edges[None].add(Item(rule, 0))
                n_item = Item(item.rule, item.index+1)
                if symbol in nullable:
                    if is_nul or n_item.rule.lhs is Ellipsis:
                        current[n_item] = None
                    elif n_item not in current:
                        edges[None].add(n_item)
                edges[symbol].add(n_item)
            else:
                accept |= item.rule.lhs is Ellipsis
                completed.add(item.rule)
        edges_out = {}
        for edge, items in edges.items():
            edge_itemset = frozenset(items)
            itemsets[edge_itemset] = (edge is None)
            edges_out[edge] = edge_itemset

        state = State(len(itemsets_out), completed, accept)
        itemsets_out[itemset] = state, current, edges_out

    if debug:
        for state, itemset, edges in itemsets_out.values():
            print "STATE {}".format(state)
            for item in itemset:
                print item
            for edge, edgeset in edges.items():
                print "GOTO {} -> {}".format(edge, itemsets_out[edgeset][0])

    for key, (state, itemset, edges) in itemsets_out.iteritems():
        for symbol, edgeset in edges.iteritems():
            if callable(symbol):
                state.conditions.add((symbol, itemsets_out[edgeset][0]))
            state.goto[symbol] = itemsets_out[edgeset][0]

    return itemsets_out[initset][0], nullable

def print_result(parser):
    for i, cell in enumerate(parser.chart):
        print 'INDEX {}'.format(i)
        for state in sorted(cell):
            print str(state).ljust(16), state[0].completed
    print 'accept', parser.accept
    print 'expect', parser.expect

def match(matcher, token):
    if callable(matcher):
        return matcher(token)
    else:
        return token.name == matcher

if __name__=='__main__':
    main()
