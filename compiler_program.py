from bincode.encoder import Function
from instruction_format import enc_code, ARG_SHIFT, ARG_LOCAL, ARG_RAW, ARG_CONST, ARG_BLOCK
from rpython.rlib.listsort import make_timsort_class

class Body(object):
    def __init__(self, blocks, functions, localv, argc, flags):
        self.blocks = reverse_postorder(blocks[0])
        self.functions = functions
        #self.is_generator = is_generator
        self.tmpc = 0
        allocate_tmp(self)
        self.argc = argc
        self.localv = localv
        self.flags = flags

    def dump(self, consttab):
        blocks = [block.dump(consttab) for block in self.blocks]
        functions = [func.dump(consttab) for func in self.functions]
        localc = len(self.localv)
        return Function(self.flags, self.tmpc, self.argc, localc, blocks, functions)

class Block(object):
    def __init__(self, index, contents, succ):
        self.index = index
        self.contents = contents
        self.succ = succ
        self.visited = False

    def __getitem__(self, index):
        return self.contents[index]

    def __len__(self):
        return len(self.contents)

    def as_arg(self, consttab):
        return self.index << ARG_SHIFT | ARG_BLOCK

    def append(self, op):
        self.contents.append(op)

    def dump(self, consttab):
        return ''.join(op.dump(consttab) for op in self)

class Constant(object):
    def __init__(self, loc, value):
        self.loc = loc
        self.value = value

    def as_arg(self, consttab):
        return consttab.get(self.value) << ARG_SHIFT | ARG_CONST

    def __repr__(self):
        return "Constant({})".format(self.value)

class Op(object):
    def __init__(self, loc, name, *args):
        self.loc = loc
        self.name = name
        self.args = args

    def dump(self, consttab):
        return enc_code(self.name, *(arg.as_arg(consttab) for arg in self.args))

    def uses(self):
        return set(arg for arg in self.args if isinstance(arg, Op))

class VOp(object):
    index = None

    def as_arg(self, consttab):
        return self.index << ARG_SHIFT | ARG_LOCAL

    def dump(self):
        return enc_code(self.name, self.as_arg(consttab),
            *(arg.as_arg(consttab) for arg in self.args))

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
            op.i = avail.pop()
        else:
            op.i = body.tmpc
            body.tmpc += 1
        stops.append((stop, op))
        sort_ends(stops).sort()
        while len(stops) > 0 and stops[0][0] < current:
            _, exp = stops.pop(0)
            assert exp.i not in avail
            avail.append(exp.i)

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
