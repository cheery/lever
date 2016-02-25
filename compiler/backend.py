# Everything that ends up into the binary goes through the
# backend.
from evaluator import optable

def new_block(exc):
    if exc:
        succ = [x.block for x in exc.trace()]
    else:
        succ = []
    return Block([], set(succ), exc)

class Function(object):
    def __init__(self, index):
        self.index = index

class Block(object):
    def __init__(self, contents, succ, exc):
        self.label = 0
        self.contents = contents
        self.succ = succ
        self.visited = False # For reverse_postorder()
        self.exc = exc

    def __getitem__(self, index):
        return self.contents[index]

    def __len__(self):
        return len(self.contents)

    def append(self, op):
        self.contents.append(op)
        self.succ.update(succ for succ in op if isinstance(succ, Block))
        for succ in self.succ:
            assert isinstance(succ, Block), type(succ)

    def op(self, loc, opname, args):
        op = Op(loc, opname, args)
        self.append(op)
        return op

class Exc(object):
    has_result = True
    index = None
    opname = "exc"
    def __init__(self, block, parent=None):
        self.block = block
        self.parent = parent
        assert len(block) == 0, "exc block must be fresh"
        block.append(self)

    def uses(self):
        return set()

    def __iter__(self):
        return iter(())

    def trace(self):
        seq = []
        while self:
            seq.append(self)
            self = self.parent
        seq.reverse()
        return seq

class Op(object):
    index = None
    def __init__(self, loc, opname, args):
        self.loc = loc
        self.opname = opname
        self.args = args
        (self.opcode, self.has_result,
         self.pattern, self.variadic) = optable.enc[opname]

    def uses(self):
        return set(arg for arg in self.args if isinstance(arg, (Op, Exc)))

    def __iter__(self):
        return iter(self.args)

def dump(flags, argc, topc, localv, entry_block, consttab, location_id, debug):
    blocks = reverse_postorder(entry_block)
    tmpc = allocate_tmp(blocks, debug)
    block = []
    for bb in blocks:
        bb.label = len(block)
        for op in bb:
            if isinstance(op, Exc):
                continue
            block.extend(encode_op(op, consttab))
    exceptions = find_exception_ranges(blocks, len(block))
    block = []
    sourcemap = []
    for bb in blocks:
        if debug:
            print "block {}".format(bb.index)
        assert bb.label == len(block)
        for op in bb:
            if isinstance(op, Exc):
                continue
            if debug:
                print "  {1} := {0} {2}".format(op.opname.ljust(12), op.index, ', '.join(map(repr_oparg, op.args)))
            codes = list(encode_op(op, consttab))
            block.extend(codes)
            sourceloc = [
                location_id,
                #(consttab.get(op.loc.path) if op.loc else -1),
                op.loc[0].col if op.loc else 0,
                op.loc[0].lno if op.loc else 0,
                op.loc[1].col if op.loc else -1,
                op.loc[1].lno if op.loc else -1
            ]
            if len(sourcemap) > 0 and sourcemap[-1][1:] == sourceloc:
                sourcemap[-1][0] += len(codes)
            else:
                sourcemap.append([len(codes)] + sourceloc)
    localc = len(localv)
    return flags, tmpc, argc, topc, localc, block, sourcemap, exceptions

def find_exception_ranges(blocks, finish):
    exceptions = []
    starts = []
    stack = []
    for block in blocks:
        new_stack = block.exc.trace() if block.exc else []
        L = len(stack) - 1
        while L >= 0 and (L >= len(new_stack) or stack[L] != new_stack[L]):
            exc = stack.pop()
            exceptions.append([starts.pop(), block.label, exc.block.label, exc.index])
            L -= 1
        stack = new_stack
        while len(starts) < len(stack):
            starts.append(block.label)
    for exc in reversed(stack):
        exceptions.append([starts.pop(), finish, exc.block.label, exc.index])
    return exceptions

def repr_oparg(arg):
    if isinstance(arg, Exc):
        return "Exc({})".format(arg.index)
    if isinstance(arg, Op):
        return "Op({})".format(arg.index)
    if isinstance(arg, Block):
        return "Block({})".format(arg.index)
    return repr(arg)

# improve this one ? 
def encode_op(op, consttab):
    assert len(op.args) >= len(op.pattern), op.opname
    assert op.variadic or len(op.args) == len(op.pattern), op.opname
    oplen = len(op.args) + op.has_result
    yield op.opcode << 8 | oplen
    if op.has_result:
        yield op.index
    vc = len(op.args) - len(op.pattern)
    for arg, vt in zip(op.args, op.pattern + [op.variadic]*vc):
        yield as_arg(op, vt, arg, consttab)

def as_arg(op, vt, arg, consttab):
    if vt == 'index':
        assert isinstance(arg, int)
        return arg
    if vt == 'vreg':
        assert isinstance(arg, (Op, Exc)), (op.opname, op.loc, arg)
        assert arg.has_result, (arg.opname, arg.loc, arg)
        return arg.index
    if vt == 'block':
        if isinstance(arg, int) and arg == 0:
            return 0
        assert isinstance(arg, Block)
        return arg.label
    if vt == 'function':
        assert isinstance(arg, Function)
        return arg.index
    if vt == 'string':
        assert isinstance(arg, unicode), (op.opname, op.loc, type(arg))
        return consttab.get(arg)
    if vt == 'constant':
        return consttab.get(arg)
    assert False, "as_arg {} ?".format(arg)

# Blocks are ordered into reverse postorder because
# it makes easier to do the following analysis on them.
def reverse_postorder(entry):
    seq = postorder_visit([], entry)
    seq.reverse()
    return seq

def postorder_visit(sequence, block):
    if block.visited:
        return
    block.visited = True
    for succ in block.succ:
        postorder_visit(sequence, succ)
    sequence.append(block)
    return sequence
# Since the frame is virtualizable now, it copies everything
# from tmp to juggle them.
# Instead of using separate index for every temporary value,
# we can do some live range analysis and reuse the indices.
# for items that quarranteely aren't simultaneously live.
def allocate_tmp(blocks, debug):
    tmpc = 0
    index = 0
    base = 0
    for block in blocks:
        block.base = base
        block.index = index
        block.depends = set()
        block.iterstop_in = set()
        block.except_in = set()
        index += 1
        base += len(block)
    # This one runs to verify the iteration stop is recognized by allocator.
    # done = False
    # while not done:
    #     done = True
    #     for block in blocks:
    #         except_ = block.except_in
    #         iterstop = block.iterstop_in
    #         for op in block:
    #             if op.opname == "iterstop" and isinstance(op.args[0], Block):
    #                 iterstop = [op.args[0]]
    #             elif op.opname == "iterstop":
    #                 iterstop = []
    #             elif op.opname == "except" and isinstance(op.args[0], Block):
    #                 except_ = op.args[0]
    #             elif op.opname == "except":
    #                 except_ = []
    #         for succ in block.succ:
    #             N = len(succ.iterstop_in) + len(succ.except_in)
    #             succ.iterstop_in.update(iterstop)
    #             succ.except_in.update(except_)
    #             M = len(succ.iterstop_in) + len(succ.except_in)
    #             if N != M:
    #                 done = False
    #for block in blocks:
    #    block.except_in.discard(block)
    #    block.succ.update(block.except_in)
    #    block.iterstop_in.discard(block)
    #    block.succ.update(block.iterstop_in)
    done = False
    while not done:
        if debug:
            print "allocate_iter"
        done = True
        for block in reversed(blocks):
            if debug:
                print "step block", block.index, [b.index for b in block.succ], [x.opname for x in block.depends]
            N = len(block.depends)
            for succ in block.succ:
                block.depends.update(succ.depends)
            for op in reversed(block):
                block.depends.discard(op)
                for use in op.uses():
                    block.depends.add(use)
            M = len(block.depends)
            if N != M:
                done = False
    live_ranges = {}
    for block in blocks:
        for op in block.depends:
            plot_range(live_ranges, op, block.base)
        for succ in block.succ:
            assert succ.index >= 0
            for op in succ.depends:
                plot_range(live_ranges, op, block.base + len(block))
        i = 0
        for op in block:
            plot_range(live_ranges, op, block.base+i)
            for use in op.uses():
                plot_range(live_ranges, use, block.base+i+1)
            i += 1
    starts = []
    stops = []
    avail = []
    for op, (start, stop) in live_ranges.iteritems():
        starts.append((start, stop, op))
    starts.sort(key=lambda x: x[0])
    if debug:
        for a,b,x in starts:
            print x.opname.rjust(20), a, b
    #sort_starts(starts).sort()
    for current, stop, op in starts:
        assert current <= stop
        if len(avail) > 0:
            op.index = avail.pop()
        else:
            op.index = tmpc
            tmpc += 1
        stops.append((stop, op))
        #sort_ends(stops).sort()
        stops.sort(key=lambda x: x[0])
        while len(stops) > 0 and stops[0][0] < current:
            _, exp = stops.pop(0)
            assert exp.index not in avail
            avail.append(exp.index)
    return tmpc

def plot_range(ranges, key, pos): 
    if key not in ranges:
        ranges[key] = (pos, pos)
    else:
        start, stop = ranges[key]
        ranges[key] = (min(start, pos), max(stop, pos))

# The previous version of this algorithm was run by RPython,
# which depended on this kind of constructs to sort.
#sort_starts = make_timsort_class(lt=lambda x, y: x[0] < y[0])
#sort_ends = make_timsort_class(lt=lambda x, y: x[0] < y[0])

class ConstantTable(object):
    def __init__(self):
        self.table = {}
        self.constants = []

    def get(self, const):
        key = type(const), const
        if key in self.table:
            return self.table[key]
        self.constants.append(const)
        self.table[key] = len(self.table)
        return self.table[key]
