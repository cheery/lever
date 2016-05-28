from rpython.rlib import jit
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rtyper.lltypesystem import rffi, lltype
import optable
import space

u16_array = lltype.GcArray(rffi.USHORT)

def from_object(obj):
    if as_i(obj.getitem(space.String(u"version"))) != 0:
        raise space.unwind(space.LError(u"bytecode version=0 required"))

    sources_list = obj.getitem(space.String(u"sources"))
    assert isinstance(sources_list, space.List)
    sources = sources_list.contents

    constants_list = obj.getitem(space.String(u"constants"))
    assert isinstance(constants_list, space.List)
    constants = constants_list.contents

    functions = []
    functions_list = obj.getitem(space.String(u"functions"))
    assert isinstance(functions_list, space.List)
    for function_list in functions_list.contents:
        flags = as_i( function_list.getitem(space.String(u"flags")))
        regc = as_i( function_list.getitem(space.String(u"regc")))
        argc = rffi.r_ulong(as_i( function_list.getitem(space.String(u"argc"))))
        topc = rffi.r_ulong(as_i( function_list.getitem(space.String(u"topc"))))
        localc = as_i( function_list.getitem(space.String(u"localc")))
        block_list = function_list.getitem(space.String(u"code"))
        sourcemap = function_list.getitem(space.String(u"sourcemap"))
        exc_table = function_list.getitem(space.String(u"exceptions"))
        assert isinstance(exc_table, space.List)
        assert isinstance(block_list, space.Uint8Array)
        block = lltype.malloc(u16_array, block_list.length/2)
        for i in range(block_list.length/2):
            a = rffi.r_long(block_list.uint8data[i*2+0])
            b = rffi.r_long(block_list.uint8data[i*2+1])
            block[i] = rffi.r_ushort((a << 8) | b)
        excs = []
        for n in exc_table.contents:
            excs.append(Exc(
                rffi.r_ulong(as_i(n.getitem(space.Integer(0)))),
                rffi.r_ulong(as_i(n.getitem(space.Integer(1)))),
                rffi.r_ulong(as_i(n.getitem(space.Integer(2)))),
                rffi.r_ulong(as_i(n.getitem(space.Integer(3)))),
            ))
        functions.append(Function(flags, regc, argc, topc, localc, block, sourcemap, excs[:]))
    return Program(Unit(constants[:], functions[:], sources[:]))

class Exc:
    _immutable_fields_ = ['start', 'stop', 'label', 'reg']
    def __init__(self, start, stop, label, reg):
        self.start = start
        self.stop = stop
        self.label = label
        self.reg = reg

def as_i(obj):
    if not isinstance(obj, space.Integer):
        raise space.unwind(space.LTypeError(u"expected integer"))
    return obj.value

class Closure(space.Object):
    _immutable_fields_ = ['parent', 'function']
    def __init__(self, frame, function):
        self.frame = frame
        self.function = function

    def call(self, argv):
        varargs = self.function.flags & 1 == 1
        argc = self.function.argc
        topc = self.function.topc
        L = len(argv)
        if L < argc:
            raise space.unwind(space.LCallError(argc, topc, varargs, L))
        # We are using this trait.
        #if L > topc and not varargs:
        #    raise space.Error(u"too many arguments [%d], from %d to %d arguments allowed" % (L, argc, topc))
        frame = Frame(self.function, self.frame.module, self.frame)
        for i in range(min(topc, L)):
            frame.local[i] = argv[i]
        if varargs:
            frame.local[topc] = space.List(argv[min(topc, L):])
        regv = new_register_array(self.function.regc)
        return interpret(0, self.function.block, regv, frame)

class Program(space.Object):
    _immutable_fields_ = ['unit']
    def __init__(self, unit):
        self.unit = unit

    def call(self, argv):
        if len(argv) != 1:
            raise space.unwind(space.LCallError(1, 1, False, len(argv)))
        module = argv[0]
        assert isinstance(module, space.Module)
        entry = self.unit.functions[0]
        frame = Frame(entry, module, None)
        regv = new_register_array(entry.regc)
        return interpret(0, entry.block, regv, frame)

class Unit:
    _immutable_fields_ = ['constants[*]', 'functions[*]', 'sources[*]']
    def __init__(self, constants, functions, sources):
        self.constants = constants
        self.functions = functions
        self.sources = sources
        for function in functions:
            function.unit = self

class Function:
    _immutable_fields_ = ['flags', 'regc', 'argc', 'topc', 'localc', 'block[*]', 'unit', 'sourcemap', 'excs[*]']
    def __init__(self, flags, regc, argc, topc, localc, block, sourcemap, excs):
        self.flags = flags
        self.regc = regc
        self.argc = argc
        self.topc = topc
        self.localc = localc
        self.block = block
        self.unit = None
        self.sourcemap = sourcemap
        self.excs = excs

class Frame:
    _immutable_fields_ = ['local', 'module', 'parent', 'unit', 'sourcemap', 'excs[*]']
    def __init__(self, function, module, parent):
        self.unit = function.unit
        self.local = [space.null for i in range(function.localc)]
        self.module = module
        self.parent = parent
        self.sourcemap = function.sourcemap
        self.excs = function.excs

class RegisterArray:
    #_virtualizable_ = ['regs[*]']
    def __init__(self, regs):
        #self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self.regs = regs

    @always_inline
    def store(self, index, value):
        self.regs[index] = value
    
    @always_inline
    def load(self, index):
        return self.regs[index]

def new_register_array(regc):
    regs = []
    for i in range(regc):
        regs.append(space.null)
    return RegisterArray(regs)

def get_printable_location(pc, block, module, unit, excs):
    return "pc=%d module=%s" % (pc, module.repr().encode('utf-8'))

jitdriver = jit.JitDriver(
    greens=['pc', 'block', 'module', 'unit', 'excs'],
    reds=['regv', 'frame'],
    #virtualizables = ['regv'],
    get_printable_location=get_printable_location)

def interpret(pc, block, regv, frame):
    module = jit.promote(frame.module)
    unit   = jit.promote(frame.unit)
    excs   = jit.promote(frame.excs)
    try:
        while pc < len(block):
            try:
                jitdriver.jit_merge_point(
                    pc=pc, block=block, module=module, unit=unit, excs=excs,
                    regv=regv, frame=frame)
                opcode = rffi.r_ulong(block[pc])>>8
                ix = pc+1
                pc = ix+(rffi.r_ulong(block[pc])&255)
                #print optable.dec[opcode][0]
                if opcode == opcode_of('assert'):
                    obj = regv.load(block[ix+0])
                    raise space.unwind(space.LAssertionError(obj))
                elif opcode == opcode_of('raise'):
                    obj = regv.load(block[ix+0])
                    traceback = obj.getattr(u"traceback")
                    if traceback is space.null:
                        traceback = space.List([])
                        obj.setattr(u"traceback", traceback)
                    elif not isinstance(traceback, space.List):
                        raise space.unwind(space.LError(u"Expected null or list as .traceback: %s" % obj.repr()))
                    raise space.Unwinder(obj, traceback)
                elif opcode == opcode_of('constant'):
                    regv.store(block[ix+0], unit.constants[block[ix+1]])
                elif opcode == opcode_of('list'):
                    contents = []
                    for i in range(ix+1, pc):
                        contents.append(regv.load(block[i]))
                    regv.store(block[ix], space.List(contents))
                elif opcode == opcode_of('move'):
                    regv.store(block[ix+0], regv.load(block[ix+1]))
                elif opcode == opcode_of('call'):
                    op_call(regv, block, ix, pc)
                elif opcode == opcode_of('callv'):
                    op_callv(regv, block, ix, pc)
                elif opcode == opcode_of('return'):
                    return regv.load(block[ix+0])
                elif opcode == opcode_of('jump'):
                    pc = rffi.r_ulong(block[ix+0])
                elif opcode == opcode_of('cond'):
                    if space.is_false(regv.load(block[ix+0])):
                        pc = rffi.r_ulong(block[ix+2])
                    else:
                        pc = rffi.r_ulong(block[ix+1])
                elif opcode == opcode_of('func'):
                    regv.store(block[ix+0],
                        Closure(frame, unit.functions[block[ix+1]]))
                elif opcode == opcode_of('iter'):
                    regv.store(block[ix+0], regv.load(block[ix+1]).iter())
                elif opcode == opcode_of('next'):
                    try:
                        regv.store(block[ix+0], regv.load(block[ix+1]).callattr(u'next', []))
                    except StopIteration as _:
                        pc = rffi.r_ulong(block[ix+2])
                # this is missing.
                #elif isinstance(op, Yield):
                #    raise YieldIteration(op.block, loop_break, op.i, regv.load(op.value.i))
                elif opcode == opcode_of('getattr'):
                    name = get_string(unit, block, ix+2)
                    obj = regv.load(block[ix+1])
                    regv.store(block[ix+0], obj.getattr(name))
                elif opcode == opcode_of('setattr'):
                    value = regv.load(block[ix+3])
                    name = get_string(unit, block, ix+2)
                    obj = regv.load(block[ix+1])
                    regv.store(block[ix+0], obj.setattr(name, value))
                elif opcode == opcode_of('getitem'):
                    index = regv.load(block[ix+2])
                    obj = regv.load(block[ix+1])
                    regv.store(block[ix+0], obj.getitem(index))
                elif opcode == opcode_of('setitem'):
                    item = regv.load(block[ix+3])
                    index = regv.load(block[ix+2])
                    obj = regv.load(block[ix+1])
                    regv.store(block[ix+0], obj.setitem(index, item))
                elif opcode == opcode_of('getloc'):
                    regv.store(block[ix+0], frame.local[block[ix+1]])
                elif opcode == opcode_of('setloc'):
                    value = regv.load(block[ix+2])
                    frame.local[block[ix+1]] = value
                    regv.store(block[ix+0], value)
                elif opcode == opcode_of('getupv'):
                    value = get_upframe(frame, block[ix+1]).local[block[ix+2]]
                    regv.store(block[ix+0], value)
                elif opcode == opcode_of('setupv'):
                    value = regv.load(block[ix+3])
                    get_upframe(frame, block[ix+1]).local[block[ix+2]] = value
                    regv.store(block[ix+0], value)
                elif opcode == opcode_of('getglob'):
                    regv.store(block[ix+0],
                        module.getattr(get_string(unit, block, ix+1)))
                elif opcode == opcode_of('setglob'):
                    regv.store(block[ix+0],
                        module.setattr(
                            get_string(unit, block, ix+1),
                            regv.load(block[ix+2])))
                elif opcode == opcode_of('not'):
                    if space.is_false(regv.load(block[ix+1])):
                        regv.store(block[ix+0], space.true)
                    else:
                        regv.store(block[ix+0], space.false)
                elif opcode == opcode_of('contains'):
                    v0 = regv.load(block[ix+1])
                    v1 = regv.load(block[ix+2])
                    if v0.contains(v1):
                        regv.store(block[ix+0], space.true)
                    else:
                        regv.store(block[ix+0], space.false)
                else:
                    raise space.unwind(space.LInstructionError(
                        optable.names.get(opcode, str(opcode)).decode('utf-8'),
                        opcode))
            except space.Unwinder as unwinder:
                #print "exception detected, doing unwinds", pc, unwinder.exception.repr()
                for exc in excs:
                    #print exc.start, exc.stop, exc.label, exc.reg
                    if exc.start < pc <= exc.stop:
                        regv.store(exc.reg, unwinder.exception)
                        pc = exc.label
                        #print "exception handler found"
                        break
                else:
                    raise
    except StopIteration as stop:
        unwinder = space.unwind(space.LUncatchedStopIteration())
        unwinder.traceback.contents.append(TraceEntry(rffi.r_long(pc), unit.sources, frame.sourcemap))
        raise unwinder
    except space.Unwinder as unwinder:
        unwinder.traceback.contents.append(TraceEntry(rffi.r_long(pc), unit.sources, frame.sourcemap))
        raise
    return space.null

class TraceEntry(space.Object):
    def __init__(self, pc, sources, sourcemap):
        self.pc = pc
        self.sources = sources
        self.sourcemap = sourcemap

@jit.unroll_safe
def op_call(regv, block, ix, pc):
    callee = regv.load(block[ix+1])
    argv = []
    for i in range(ix+2, pc):
        argv.append(regv.load(block[i]))
    regv.store(block[ix], callee.call(argv))

@jit.unroll_safe
def op_callv(regv, block, ix, pc):
    callee = regv.load(block[ix+1])
    argv = []
    for i in range(ix+2, pc-1):
        argv.append(regv.load(block[i]))
    extend_iter(argv, regv.load(block[pc-1]))
    regv.store(block[ix], callee.call(argv))

def extend_iter(seq, obj):
    it = obj.iter()
    while True:
        try:
            seq.append(it.callattr(u"next", []))
        except StopIteration as _:
            return

@jit.unroll_safe
def get_upframe(frame, index):
    parent = frame.parent
    for i in range(index):
        parent = parent.parent
    return parent

@specialize.memo()
def opcode_of(opname):
    return optable.enc[opname][0]

@always_inline
def get_string(unit, block, i):
    obj = unit.constants[block[i]]
    assert isinstance(obj, space.String)
    return obj.string
