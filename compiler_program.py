from rpython.rlib.listsort import make_timsort_class
from evaluator import optable

class Function(object):
    def __init__(self, index, flags, argc, localv, blocks):
        self.index = index
        self.blocks = reverse_postorder(blocks[0])
        #self.is_generator = is_generator
        self.tmpc = 0
        allocate_tmp(self)
        self.argc = argc
        self.localv = localv
        self.flags = flags

    def as_arg(self, consttab, vt):
        assert vt == 'function'
        return self.index

    def dump(self, consttab):
        block = []
        for bb in self.blocks:
            bb.label = len(block)
            block.extend(bb.dump(consttab))
        block = []
        for bb in self.blocks:
            assert bb.label == len(block)
            block.extend(bb.dump(consttab))
        localc = len(self.localv)
        return self.flags, self.tmpc, self.argc, localc, block

class Block(object):
    def __init__(self, index, contents, succ):
        self.label = 0
        self.index = index
        self.contents = contents
        self.succ = succ
        self.visited = False

    def __getitem__(self, index):
        return self.contents[index]

    def __len__(self):
        return len(self.contents)

    def as_arg(self, consttab, vt):
        assert vt == 'block'
        return self.label

    def append(self, op):
        self.contents.append(op)
        self.succ.update(succ for succ in op if isinstance(succ, Block))

    def dump(self, consttab):
        result = []
        for op in self:
            result.extend(op.dump(consttab))
        return result

class Constant(object):
    def __init__(self, value):
        self.value = value

    def as_arg(self, consttab, vt):
        assert vt == 'constant' or vt == 'string' and isinstance(self.value, (str, unicode))
        return consttab.get(self.value)

    def __repr__(self):
        return "Constant({})".format(self.value)

class Op(object):
    index = None

    def __init__(self, loc, opname, args):
        self.loc = loc
        self.args = args
        self.opname = opname
        (self.opcode, self.has_result,
         self.pattern, self.variadic) = optable.enc[opname]

    def as_arg(self, consttab, vt):
        assert vt == 'vreg'
        assert self.has_result
        return self.index

    def dump(self, consttab):
        assert len(self.args) >= len(self.pattern), self.opname
        assert self.variadic or len(self.args) == len(self.pattern), self.opname
        oplen = len(self.args) + self.has_result
        yield self.opcode << 8 | oplen
        if self.has_result:
            yield self.index
        vc = len(self.args) - len(self.pattern)
        for arg, vt in zip(self.args, self.pattern + [self.variadic]*vc):
            if isinstance(arg, int):
                assert vt == 'index'
                yield arg
            else:
                yield arg.as_arg(consttab, vt)

    def uses(self):
        return set(arg for arg in self.args if isinstance(arg, Op))

    def __iter__(self):
        return iter(self.args)

# Blocks are ordered into reverse postorder because
# it makes easier to do some analysis on them.
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
def allocate_tmp(body):
    index = 0
    base = 0
    for block in body.blocks:
        block.base = base
        block.index = index
        block.depends = {}
        index += 1
        base += len(block)
    done = False
    while not done:
        done = True
        for block in reversed(body.blocks):
            N = len(block.depends)
            for succ in block.succ:
                block.depends.update(succ.depends)
            for op in reversed(block):
                if op in block.depends:
                    block.depends.pop(op)
                for use in op.uses():
                    block.depends[use] = None
            M = len(block.depends)
            if N < M:
                done = False
    live_ranges = {}
    for block in body.blocks:
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
    sort_starts(starts).sort()
    for current, stop, op in starts:
        assert current <= stop
        if len(avail) > 0:
            op.index = avail.pop()
        else:
            op.index = body.tmpc
            body.tmpc += 1
        stops.append((stop, op))
        sort_ends(stops).sort()
        while len(stops) > 0 and stops[0][0] < current:
            _, exp = stops.pop(0)
            assert exp.index not in avail
            avail.append(exp.index)

def plot_range(ranges, key, pos): 
    if key not in ranges:
        ranges[key] = (pos, pos)
    else:
        start, stop = ranges[key]
        ranges[key] = (min(start, pos), max(stop, pos))

# The previous version of this algorithm was run by RPython,
# which depended on this kind of constructs to sort.
sort_starts = make_timsort_class(lt=lambda x, y: x[0] < y[0])
sort_ends = make_timsort_class(lt=lambda x, y: x[0] < y[0])
