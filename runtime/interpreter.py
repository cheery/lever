from objects.core import *
from objects.modules import *
from vmoptable import *
# from context import construct_coeffect
import os

def read_script(code, preset, env, src):
    module = Module()
    for key, value in preset.items():
        set_attribute(module, wrap(key), value)
    code = as_dict(code)
    # At first I thought that I wouldn't do this right yet, but one weekday
    # when Internet connection was cut out, I decided I'd like some better
    # error messages.
    sources = []
    src_dir = os.path.abspath(rpython_dirname(src.encode('utf-8')))
    for w_src in as_list(attr(code, u"sources")):
        abs_src = os.path.join(src_dir, 
            cast(w_src, String).string.encode('utf-8'))
        sources.append(String(abs_src.decode('utf-8')))

    unit = Unit(
        constants = as_list(attr(code, u"constants")),
        env = env,
        module = module,
        program = as_list(attr(code, u"program")),
        sources = sources)
    loc = SourceLocBuilder(-1,
        as_list(attr(as_dict(unit.program[0]), u"sourcemap")), sources)
    return Closure(0, 0, unit, [0], [], loc), module

# RPython cannot ensure that the 'i' is nonzero, so it refuses to compile this
# without modifications.
def rpython_dirname(p):
    """Returns the directory component of a pathname"""
    i = p.rfind('/') + 1
    if i >= 0:
        head = p[:i]
    else:
        head = ""
    if head and head != '/'*len(head):
        head = head.rstrip('/')
    return head

@builtin(3)
def w_inspect(closure):
    closure = cast(closure, Closure)
    return Tuple([closure.unit,
        ImmutableList(closure.frame[:]),
        ImmutableList([wrap(i) for i in closure.entries]) ])

VMUnitKind = Kind()
class Unit(Object):
    static_kind = VMUnitKind
    def __init__(self, constants, env, module, program, sources):
        self.constants = constants
        self.env = env
        self.module = module
        self.program = program
        self.sources = sources

ClosureKind = Kind()
class Closure(KObject):
    static_kind = ClosureKind
    def __init__(self, inc, outc, unit, entries, frame, loc):
        self.inc = inc
        self.outc = outc
        self.unit = unit
        self.entries = entries
        self.loc = loc
        self.frame = frame
        KObject.__init__(self)

class FreshGenerator(Iterator):
    def __init__(self, unit, proc, frame):
        self.unit = unit
        self.proc = proc
        self.frame = frame
 
    def next(self):
        stack = [enter_proc(self.unit, self.proc, self.frame, [])]
        return step_generator(self.unit, stack)

class LiveGenerator(Iterator):
    def __init__(self, unit, stack, front):
        self.unit = unit
        self.stack = stack
        self.front = front

    def next(self):
        if self.front is not None:
            try:
                value, front = self.front.next()
                return value, LiveGenerator(self.unit, self.stack, front)
            except StopIteration:
                pass
        stack = snapshot_stack(self.stack)
        return step_generator(self.unit, stack)

def step_generator(unit, stack):
    stack, value, stack_generators = interpreter_loop(unit, stack, True)
    if stack_generators:
        front = cast(value, Iterator)
        return LiveGenerator(unit, stack, front).next()
    elif value is None:
        raise StopIteration()
    else:
        return value, LiveGenerator(unit, stack, None)

# json-as-bytecode is supposed to be a temporary measure,
# but who knows how long we will have it. It already shows
# that it was the right choice at the beginning,
# may not be that great later. Well it's easy to replace fortunately.
def closure_call(closure, args):
    closure = cast(closure, Closure)
    result = [None for k in range(closure.outc)]
    inputs = closure.frame + args
    outputs = [(result, k) for k in range(closure.outc)]
    proc = enter_closure(closure.unit, closure, len(inputs), len(outputs))
    stack = [enter_proc(closure.unit, proc, inputs, outputs)]
    interpreter_loop(closure.unit, stack)
    assert None not in result
    return result
ClosureKind.properties[op_call] = BuiltinPortal(closure_call)

def enter_closure(unit, closure, inc, outc):
    i = closure.inc
    opt  = len(closure.entries) - 1
    if (not (i-opt <= inc <= i)) or outc != closure.outc:
        tb = error(e_TypeError)
        tb.trace.append(closure.loc)
        raise tb
    entry = closure.entries[i - inc]
    return as_dict(unit.program[entry])

def enter_proc(unit, proc, inputs, outputs, xc=None):
    tmp = [None] * unwrap_int(attr(proc, u"tmpc"))
    body = as_list(attr(proc, u"body"))
    smap = as_list(attr(proc, u"sourcemap"))
    ctx = Context(tmp, inputs, outputs, unit.constants)
    return (ctx, (body, smap), 0, xc)

@specialize.arg(2)
def interpreter_loop(unit, stack, is_generator=False):
    while len(stack) > 0:
        ctx, (body, smap), index, xc = stack.pop(-1)
        try:
            result = eval_body(unit, ctx, body, smap, index)
            if isinstance(result, Done):
                assert ctx.all_outputs_written()
            elif isinstance(result, Branch):
                if result.exc >= 0:
                    stxc = ExceptionCatch(len(stack), result.exc)
                else:
                    stxc = None
                if at_nonterminal(body, result.index) or stxc is not None:
                    stack.append((ctx, (body, smap), result.index, xc))
                stack.append(enter_proc(unit,
                    result.proc, result.inputs, result.outputs, stxc))
            elif isinstance(result, Yield) and is_generator:
                if at_nonterminal(body, result.index):
                    stack.append((ctx, (body, smap), result.index, xc))
                value = result.value
                if (result.stack_generators
                    and isinstance(value, FreshGenerator)
                    and value.unit is unit):
                    stack.append(enter_proc(unit,
                        value.proc, value.frame, []))
                else:
                    return stack, result.value, result.stack_generators
            else:
                raise error(e_EvalError)
        except OperationError as tb:
            tb.trace.append(SourceLocBuilder(index, smap, unit.sources))
            if xc is None:
                for _, (_, smap), pc, _ in reversed(stack):
                    tb.trace.append(SourceLocBuilder(pc, smap, unit.sources))
                raise
            for _, (_, smap), pc, _ in reversed(stack[xc.k:len(stack)]):
                tb.trace.append(SourceLocBuilder(pc, smap, unit.sources))
            stack[xc.k:len(stack)] = []
            ctx, (body, smap), pc, xc = stack.pop(-1)
            index, opcode = decode_opcode(body, xc.index)
            if opcode != o_terminal:
                tb = error(e_EvalError)
                tb.trace.append(SourceLocBuilder(pc, smap, unit.sources))
                raise tb
            index, outputs = decode_list(body, index)
            if len(outputs) != 1:
                tb = error(e_EvalError)
                tb.trace.append(SourceLocBuilder(pc, smap, unit.sources))
                raise tb
            tb.trace.append(SourceLocBuilder(pc, smap, unit.sources))
            ctx.write(outputs[0], tb.error)
            stack.append((ctx, (body, smap), index, xc))
    if is_generator:
        return stack, None, False

def eval_body(unit, ctx, body, smap, index):
    while True:
        pc = index
        index, opcode = decode_opcode(body, index)
        flag = opcode & 7
        if flag == o_simple:
            index, iv = decode_list(body, index)
            index, ov = decode_list(body, index)
            if opcode == o_move:
                seq = [ctx.read(i) for i in iv]
                motion(ctx, seq, ov)
            elif opcode == o_global and len(iv) == 1 and len(ov) > 0:
                seq = [load_global(unit, ctx.read(iv[0]))]
                motion(ctx, seq, ov)
            elif opcode == o_global and len(iv) > 1 and len(ov) == 0:
                name = ctx.read(iv[0])
                seq = [ctx.read(i) for i in iv[1:]]
                set_attribute(unit.module, name, pack(seq))
            elif opcode == o_attr and len(iv) == 2 and len(ov) > 0:
                base = ctx.read(iv[0])
                name = ctx.read(iv[1])
                seq = [get_attribute(base, name)]
                motion(ctx, seq, ov)
            elif opcode == o_attr and len(iv) > 2 and len(ov) == 0:
                base = ctx.read(iv[0])
                name = ctx.read(iv[1])
                value = pack([ctx.read(i) for i in iv[2:]])
                set_attribute(base, name, value)
            elif opcode == o_item and len(iv) == 2 and len(ov) > 0:
                base = ctx.read(iv[0])
                indexer = ctx.read(iv[1])
                seq = [call(op_getitem, [base, indexer])]
                motion(ctx, seq, ov)
            elif opcode == o_item and len(iv) > 2 and len(ov) == 0:
                base = ctx.read(iv[0])
                indexer = ctx.read(iv[1])
                value = pack([ctx.read(i) for i in iv[2:]])
                call(op_setitem, [base, indexer, value], 0)
            elif opcode == o_true and len(iv) == 0 and len(ov) == 1:
                ctx.write(ov[0], true)
            elif opcode == o_false and len(iv) == 0 and len(ov) == 1:
                ctx.write(ov[0], false)
            elif opcode == o_call and len(iv) >= 1:
                try:
                    callee = ctx.read(iv[0])
                    args = [ctx.read(i) for i in iv[1:]]
                    if isinstance(callee, Closure) and callee.unit is unit and callee.outc == len(ov):
                        inputs = callee.frame + args
                        outputs = [ctx.addr(o) for o in ov]
                        proc = enter_closure(unit, callee,
                            len(inputs), len(outputs))
                        return Branch(index, proc, inputs, outputs)
                    out = callv(callee, args)
                    motion(ctx, out, ov)
                except OperationError as tb:
                    loc = SourceLocBuilder(index, smap, unit.sources)
                    tb.trace.append(loc)
                    raise
            elif opcode == o_deref and len(iv) == 1 and len(ov) > 0:
                base = ctx.read(iv[0])
                seq = [call(op_getslot, [base])]
                motion(ctx, seq, ov)
            elif opcode == o_deref and len(iv) > 1 and len(ov) == 0:
                base = ctx.read(iv[0])
                value = pack([ctx.read(i) for i in iv[1:]])
                call(op_setslot, [base, value], 0)
            else:
                raise error(e_EvalError)
        elif flag == o_branch:
            index, iv = decode_list(body, index)
            index, ov = decode_list(body, index)
            return Branch(index, as_dict(unit.program[opcode >> 3]),
                [ctx.read(i) for i in iv],
                [ctx.addr(o) for o in ov])
        elif flag == o_frame:
            index, iv = decode_list(body, index)
            index, ov = decode_list(body, index)
            frame = []
            closures = []
            for o in ov:
                index, in_frame, is_generator, entries = decode_frame(body, index)
                if is_generator:
                    proc = as_dict(unit.program[entries[0]])
                    obj = FreshGenerator(unit, proc, frame)
                else:
                    proc = as_dict(unit.program[entries[0]])
                    inc  = unwrap_int(attr(proc, u"inc"))
                    outc = unwrap_int(attr(proc, u"outc"))
                    loc = SourceLocBuilder(index, smap, unit.sources)
                    obj = Closure(inc, outc, unit, entries, frame, loc)
                if in_frame:
                    frame.append(obj)
                closures.append((o, obj))
            frame.extend([ctx.read(i) for i in iv])
            for o, cl in closures:
                ctx.write(o, cl)
        elif flag == o_branchx:
            index, iv = decode_list(body, index)
            index, ov = decode_list(body, index)
            index, x  = decode_jump(body, index)
            return Branch(index, as_dict(unit.program[opcode >> 3]),
                [ctx.read(i) for i in iv],
                [ctx.addr(o) for o in ov], x)
        elif flag == o_ionly:
            index, iv = decode_list(body, index)
            if opcode == o_raise and len(iv) == 1:
                raise OperationError(ctx.read(iv[0]))
            elif opcode == o_yield and len(iv) == 1:
                return Yield(index, ctx.read(iv[0]))
            elif opcode == o_yield_from and len(iv) == 1:
                return Yield(index, ctx.read(iv[0]), True)
            else:
                raise error(e_EvalError)
        elif flag == o_guard:
            index, iv = decode_list(body, index)
            index, ov = decode_list(body, index)
            index, x  = decode_jump(body, index)
            if opcode == o_is_true and len(iv) == 1:
                if ctx.read(iv[0]) is false:
                    index, opcode = decode_opcode(body, x)
                    index, outputs = decode_list(body, index)
                    if opcode != o_terminal:
                        raise error(e_EvalError)
            elif opcode == o_eq and len(iv) == 2:
                val = call(op_eq, [ctx.read(iv[0]), ctx.read(iv[1])])
                if not unwrap_bool(val):
                    index, opcode = decode_opcode(body, x)
                    index, outputs = decode_list(body, index)
                    if opcode != o_terminal:
                        raise error(e_EvalError)
            elif opcode == o_match and len(iv) == 2:
                pattern = ctx.read(iv[0])
                val = ctx.read(iv[1])
                if not unwrap_bool(call(op_match, [pattern, val], 1)):
                    index, opcode = decode_opcode(body, x)
                    index, outputs = decode_list(body, index)
                    if opcode != o_terminal:
                        raise error(e_EvalError)
                elif len(ov) > 0:              # The matcher does not always
                                               # need to extract anything.
                    out = callv(op_unpack, [pattern, val])
                    motion(ctx, out, ov)
            elif opcode == o_next and len(iv) > 0:
                it = ctx.read(iv[0])
                it = cast(it, Iterator)
                try:
                    value, it = it.next()
                    motion(ctx, [value, it], ov)
                except StopIteration:
                    index, opcode = decode_opcode(body, x)
                    if opcode != o_terminal:
                        raise error(e_EvalError)
                    index, outputs = decode_list(body, index)
        elif flag == o_terminal:
            return Done()
        else:
            raise error(e_EvalError)
    return Done()

def decode_opcode(body, index):
    opcode = unwrap_int(body[index])
    return index+1, opcode

def at_nonterminal(body, index):
    opcode = unwrap_int(body[index])
    return opcode != o_terminal

def decode_list(body, index):
    count = unwrap_int(body[index])
    k0 = index+1
    k1 = index+count+1
    result = [unwrap_int(body[k]) for k in range(k0, k1)]
    return k1, result

def decode_frame(body, index):
    info = unwrap_int(body[index])
    in_frame = (info & 1 == 1)
    is_generator = (info & 2 == 2)
    count = info >> 2
    k0 = index+1
    k1 = index+count+1
    entries = [unwrap_int(body[k]) for k in range(k0, k1)]
    return k1, in_frame, is_generator, entries

def decode_jump(body, index):
    offset = unwrap_int(body[index])
    return index+1, index+1+offset

# This operation only works on generators, because they have no
# external outputs.
def snapshot_stack(stack):
    n_tmp_v = []
    n_outputs_v = []
    n_stack = []
    # Copying the tmp and redirecting output references is sufficient
    # for producing a copy. 
    for i, (ctx, body, index, xc) in enumerate(stack):
        n_tmp_v.append(list(ctx.tmp))
        if len(ctx.tmp) > 0:
            ctx.tmp[0] = wrap(i)
    for i, (ctx, body, index, xc) in enumerate(stack):
        n_outputs = []
        for tmp, n in ctx.outputs:
            n_tmp = n_tmp_v[unwrap_int(tmp[0])]
            n_outputs.append((n_tmp, n))
        n_outputs_v.append(n_outputs)
    for i, (ctx, body, index, xc) in enumerate(stack):
        ctx.tmp[0] = n_tmp_v[unwrap_int(ctx.tmp[0])][0]
        n_ctx = Context(n_tmp_v[i],
            ctx.inputs, n_outputs_v[i], ctx.constants)
        n_stack.append((n_ctx, body, index, xc))
    return n_stack

class ExceptionCatch:
    def __init__(self, k, index):
        self.k = k
        self.index = index

class Context:
    def __init__(self, tmp, inputs, outputs, constants):
        self.tmp = tmp
        self.inputs = inputs
        self.outputs = outputs
        self.constants = constants

    def read(self, ix):
        flag = ix&3
        if flag == 0:
            value = self.tmp[ix >> 2]
            assert value is not None
            return value
        elif flag == 1:
            return self.inputs[ix >> 2]
        elif flag == 2:
            slots, n = self.outputs[ix >> 2]
            value = slots[n]
            assert value is not None, ix >> 2
            return value
        else:
            return self.constants[ix >> 2]

    def write(self, ix, value):
        flag = ix&3
        if flag == 0:
            self.tmp[ix >> 2] = value
        elif flag == 2:
            slots, n = self.outputs[ix >> 2]
            slots[n] = value
        else:
            assert False, "this ought not happen"

    def addr(self, ix):
        flag = ix&3
        if flag == 0:
            return self.tmp, ix >> 2
        elif flag == 2:
            return self.outputs[ix >> 2]
        else:
            assert False, "this ought not happen"

    def all_outputs_written(self):
        for slots, n in self.outputs:
            if slots[n] is None:
                return False
        return True

def motion(ctx, seq, ov):
    ic = len(seq)
    oc = len(ov)
    if ic == oc:
        for i, val in enumerate(seq):
            ctx.write(ov[i], val)
    elif ic == 1:
        seq = cast(seq[0], Tuple).items
        if len(seq) != oc:
            raise error(e_TypeError)
        for i, val in enumerate(seq):
            ctx.write(ov[i], val)
    elif oc == 1 and ic != 0:
        ctx.write(ov[0], Tuple(seq))
    else:
        raise error(e_EvalError)

def pack(seq):
    if len(seq) == 1:
        return seq[0]
    elif len(seq) == 0:
        raise error(e_EvalError)
    else:
        return Tuple(seq)

class Result:
    pass

class Done(Result):
    def __init__(self):
        pass

class Yield(Result):
    def __init__(self, index, value, stack_generators=False):
        self.index = index
        self.value = value
        self.stack_generators = stack_generators

class Branch(Result):
    def __init__(self, index, proc, inputs, outputs, exc=-1):
        self.index = index
        self.proc = proc
        self.inputs = inputs
        self.outputs = outputs
        self.exc = exc

SourceLocBuilderKind = Kind()
class SourceLocBuilder(Object):
    static_kind = SourceLocBuilderKind
    def __init__(self, pc, smap, sources):
        assert isinstance(pc, int)
        assert isinstance(smap, list)
        assert isinstance(sources, list)
        self.pc      = pc
        self.smap    = smap
        self.sources = sources

    def build_loc(self):
        pc = self.pc
        if pc == -1:
            return [wrap(0)] * 5, self.sources
        i = 0
        while i+6 <= len(self.smap):
            bytek = unwrap_int(self.smap[i])
            if pc <= bytek:
                col0 = self.smap[i+1]
                lno0 = self.smap[i+2]
                col1 = self.smap[i+3]
                lno1 = self.smap[i+4]
                srci = self.smap[i+5]
                return [col0, lno0, col1, lno1, srci], self.sources
            pc -= bytek
            i += 6
        return [wrap(0)] * 5, self.sources

# Still missing:
#   deref
#   source locations

# 'bind' instruction may be necessary for importing stuff from
# other modules. And should use ! -syntax for describing mutables.

# module = cast(eval_expr(ctx, as_dict(attr(val, u"module"))), Module)
# for dst, src in as_dict(attr(val, u"bindings")).iteritems():
#     ctx.module.bind(as_string(dst), module, as_string(src))
#
# Coeffects will inevitably need some special support from the vm.
#
# slot = eval_slot(ctx, as_dict(attr(val, u"slot")))
# fields = []
# for prop in as_list(attr(val, u"fields")):
#     prop = as_dict(prop)
#     name = as_string(attr(prop, u"name"))
#     mutable = unwrap_bool(attr(prop, u"mutable"))
#     fields.append((name, mutable))
# coeffect = construct_coeffect(fields, ctx.module)
# slot.store(ctx, coeffect)

# Here's how record construction works.
#    fields = []
#    for prop in as_list(attr(val, u"fields")):
#        prop = as_dict(prop)
#        name = as_string(attr(prop, u"name"))
#        mutable = unwrap_bool(attr(prop, u"mutable"))
#        value = eval_expr(ctx, as_dict(attr(prop, u"value")))
#        fields.append((name, mutable, value))
#    return construct_record(fields)

def load_global(unit, name):
    string = cast(name, String).string
    if string in unit.module.cells:
        return get_attribute(unit.module, name)
    for module in unit.env:
        if string in module.cells:
            return get_attribute(module, name)
    raise error(e_NoAttr, name)


def attr(val, name):
    return val[String(name)]

def as_string(val):
    return cast(val, String).string

def as_list(val):
    return cast(val, List).contents

def as_dict(val):
    return cast(val, Dict).table

variables = {
    u"VMUnitKind": VMUnitKind,
    u"ClosureKind": ClosureKind,
    u"inspect": w_inspect,
}

@getter(Unit, u"constants", 1)
def Unit_get_constants(unit):
    unit = cast(unit, Unit)
    return ImmutableList(unit.constants[:])

@getter(Unit, u"env", 1)
def Unit_get_env(unit):
    unit = cast(unit, Unit)
    return ImmutableList(unit.env[:])

@getter(Unit, u"module", 1)
def Unit_get_module(unit):
    unit = cast(unit, Unit)
    return unit.module

@getter(Unit, u"program", 1)
def Unit_get_program(unit):
    unit = cast(unit, Unit)
    program = []
    for proc in unit.program:
        table = empty_r_dict()
        if not isinstance(proc, Dict):
            raise error(e_EvalError)
        for key, value in proc.table.iteritems():
            if isinstance(value, List):
                value = call(op_snapshot, [value])
            table[key] = value
        program.append(ImmutableDict(table))
    return ImmutableList(program)

@getter(Unit, u"sources", 1)
def Unit_get_sources(unit):
    unit = cast(unit, Unit)
    return ImmutableList(unit.sources[:])
