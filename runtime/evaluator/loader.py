from rpython.rlib import jit, rvmprof
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.rlib.rstackovf import StackOverflow
from rpython.rtyper.lltypesystem import rffi, lltype
from sourcemaps import TraceEntry, raw_pc_location
import pathobj
import optable
import space

#u16_array = lltype.GcArray(rffi.USHORT)

def from_object(obj, path):
    if as_i(obj.getitem(space.String(u"version"))) != 0:
        raise space.unwind(space.LError(u"bytecode version=0 required"))

    sources = as_list(obj.getitem(space.String(u"sources")))
    constants = as_list(obj.getitem(space.String(u"constants")))

    functions = []
    for function_list in as_list(obj.getitem(space.String(u"functions"))):
        flags = as_i( function_list.getitem(space.String(u"flags")))
        regc = as_i( function_list.getitem(space.String(u"regc")))
        argc = rffi.r_ulong(as_i( function_list.getitem(space.String(u"argc"))))
        topc = rffi.r_ulong(as_i( function_list.getitem(space.String(u"topc"))))
        localc = as_i( function_list.getitem(space.String(u"localc")))
        block_list = as_u8a(function_list.getitem(space.String(u"code")))
        sourcemap = function_list.getitem(space.String(u"sourcemap"))
        exc_table = as_list(function_list.getitem(space.String(u"exceptions")))
        block = [getindex_u16(block_list, i)
            for i in range(block_list.length / 2)]
        #block = lltype.malloc(u16_array, block_list.length/2)
        #for i in range(block_list.length/2):
        #    a = rffi.r_long(block_list.uint8data[i*2+0])
        #    b = rffi.r_long(block_list.uint8data[i*2+1])
        #    block[i] = rffi.r_ushort((a << 8) | b)
        excs = [Exc(
            rffi.r_ulong(as_i(n.getitem(space.Integer(0)))),
            rffi.r_ulong(as_i(n.getitem(space.Integer(1)))),
            rffi.r_ulong(as_i(n.getitem(space.Integer(2)))),
            rffi.r_ulong(as_i(n.getitem(space.Integer(3)))))
            for n in exc_table]
        varnames = space.null                                           # Backwards compatible approach.
        if function_list.contains(space.String(u"varnames")):           # Consider improvements in the major release.
            varnames = function_list.getitem(space.String(u"varnames"))
        functions.append(Function(flags, regc, argc, topc, localc, block, sourcemap, excs[:], varnames))
    return Program(Unit(constants[:], functions[:], sources[:], path))

def getindex_u16(block_list, i):
    a = rffi.r_long(block_list.uint8data[i*2+0])
    b = rffi.r_long(block_list.uint8data[i*2+1])
    return rffi.r_ushort((a << 8) | b)

class Exc:
    _immutable_fields_ = ['start', 'stop', 'label', 'reg']
    def __init__(self, start, stop, label, reg):
        self.start = start
        self.stop = stop
        self.label = label
        self.reg = reg

def as_list(obj):
    if not isinstance(obj, space.List):
        raise space.unwind(space.LTypeError(u"expected list"))
    return obj.contents

def as_u8a(obj):
    if not isinstance(obj, space.Uint8Data):
        raise space.unwind(space.LTypeError(u"expected uint8array"))
    return obj

def as_i(obj):
    if not isinstance(obj, space.Integer):
        raise space.unwind(space.LTypeError(u"expected integer"))
    return obj.value

class Closure(space.Object):
    _immutable_fields_ = ['parent', 'frame', 'function']
    def __init__(self, frame, function):
        self.frame = frame
        self.function = function
        self.doc = space.null

    def call(self, argv):
        frame = create_frame(self.frame, self.function, argv)
        #regv = new_register_array(self.function.regc)
        # shoving registers into the frame provided a valuable optimization.
        # TODO: but it also means that some work needs to be done
        # to improve the upscope here.
        if jit.promote(self.function.flags & 2 != 0):
            return Generator(0, self.function.block, frame)
        else:
            return interpret(0, self.function.block, frame)

    def getattr(self, name):
        if name == u"doc":
            return self.doc
        elif name == u"loc":
            return sourceloc_introspection(0, self.function)
        elif name == u"spec":
            spec = space.Exnihilo()
            spec.setattr(u'argc', space.Integer(rffi.r_long(self.function.argc)))
            spec.setattr(u'optional', space.Integer(rffi.r_long(self.function.topc - self.function.argc)))
            spec.setattr(u'is_variadic', space.boolean(self.function.flags & 1 == 1))
            spec.setattr(u'varnames', self.function.varnames)
            return spec
        elif name == u"code":
            return Introspection(self)
        else:
            return space.Object.getattr(self, name)

    def setattr(self, name, value):
        if name == u"doc":
            self.doc = value
            return space.null
        else:
            return space.Object.setattr(self, name, value)

    def listattr(self):
        listing = space.Object.listattr(self)
        listing.append(space.String(u"doc"))
        listing.append(space.String(u"source_location"))
        listing.append(space.String(u"spec"))
        listing.append(space.String(u"code"))
        return listing

@jit.unroll_safe
def create_frame(parent, function, argv):
    varargs = jit.promote(function.flags & 1 == 1)
    argc = function.argc
    topc = function.topc
    L = len(argv)
    if L < argc:
        # The pc=0 refers to the function itself. This entry
        # is really helpful when trying to determine the origin of a CallError.
        head_entry = TraceEntry(rffi.r_long(0),
            function.unit.sources,
            function.sourcemap, function.unit.path)
        unwinder = space.unwind(space.LCallError(argc, topc, varargs, L))
        unwinder.traceback.contents.append(head_entry)
        raise unwinder
    # We are using this trait.
    #if L > topc and not varargs:
    #    raise space.Error(u"too many arguments [%d], from %d to %d arguments allowed" % (L, argc, topc))
    frame = Frame(function, parent.module, parent, function.regc)
    A = min(topc, L)
    for i in range(A):
        frame.store_local(i, argv[i])
    if varargs:
        frame.store_local(topc, space.List(argv[A:]))
    return frame

class Generator(space.Object):
    def __init__(self, pc, block, frame):
        self.pc = pc
        self.block = block
        self.frame = frame

    def iter(self):
        return self

@Generator.method(u"next", space.signature(Generator))
def Generator_next(self):
    if self.frame is None:
        raise StopIteration()
    try:
        interpret(self.pc, self.block, self.frame)
        self.frame = None
        self.block = None #self.block = lltype.nullptr(u16_array)
        raise StopIteration()
    except Yield as yi:
        self.pc = yi.pc
        return yi.value
    
class Yield(Exception):
    def __init__(self, pc, value):
        self.pc = pc
        self.value = value

class Program(space.Object):
    _immutable_fields_ = ['unit']
    def __init__(self, unit):
        self.unit = unit

    def call(self, argv):
        if len(argv) != 1:
            raise space.unwind(space.LCallError(1, 1, False, len(argv)))
        module = argv[0]
        if not isinstance(module, space.Module):
            raise space.unwind(space.LError(u"Argument to program must be a module"))
        entry = self.unit.functions[0]
        frame = Frame(entry, module, None, entry.regc)
        #regv = new_register_array(entry.regc)
        return interpret(0, entry.block, frame)

class Unit:
    _immutable_fields_ = ['constants[*]', 'functions[*]', 'sources[*]', 'path']
    def __init__(self, constants, functions, sources, path):
        self.constants = constants
        self.functions = functions
        self.sources = sources
        self.path = path
        for function in functions:
            function.unit = self
            rvmprof.register_code(function, get_function_name)

class Function(space.Object):
    _immutable_fields_ = ['flags', 'regc', 'argc', 'topc', 'localc', 'block[*]', 'unit', 'sourcemap', 'excs[*]', 'varnames']
    def __init__(self, flags, regc, argc, topc, localc, block, sourcemap, excs, varnames):
        self.flags = flags
        self.regc = regc
        self.argc = argc
        self.topc = topc
        self.localc = localc
        self.block = block
        self.unit = None
        self.sourcemap = sourcemap
        self.excs = excs
        self.varnames = varnames

class Frame:
    _immutable_fields_ = ['function', 'local', 'module', 'parent', 'unit', 'sourcemap', 'excs[*]', 'regs']
    _virtualizable_ = ['local[*]', 'regs[*]']
    def __init__(self, function, module, parent, regc):
        self = jit.hint(self, access_directly=True, fresh_virtualizable=True)
        self.function = function
        self.unit = function.unit
        self.local = [None] * function.localc
        self.module = module
        self.parent = parent
        self.sourcemap = function.sourcemap
        self.excs = function.excs
        self.regs = [None] * regc

    @always_inline
    def store_local(self, index, value):
        self.local[index] = value
    
    @always_inline
    def load_local(self, index):
        value = self.local[index]
        if value is None:
            return space.null
        return value

    @always_inline
    def store(self, index, value):
        self.regs[index] = value
    
    @always_inline
    def load(self, index):
        value = self.regs[index]
        if value is None:
            return space.null
        return value

# class RegisterArray:
# #    _virtualizable_ = ['regs[*]']
#     _immutable_fields_ = ['regs']
#     def __init__(self, regs):
#         self.regs = regs
# 
#     @always_inline
#     def store(self, index, value):
#         self.regs[index] = value
#     
#     @always_inline
#     def load(self, index):
#         return self.regs[index]
# 
# def new_register_array(regc):
#     regs = []
#     for i in range(regc):
#         regs.append(space.null)
#     return RegisterArray(regs)

def get_function_name(function):
    entry = TraceEntry(rffi.r_long(0),
        function.unit.sources,
        function.sourcemap, function.unit.path)
    source, col0, lno0, col1, lno1 = entry.pc_location()
    if isinstance(source, pathobj.Path):
        source = pathobj.Path_to_string(source)
    if isinstance(source, space.String):
        src = source.string.encode('utf-8')
    else:
        src = source.repr().encode('utf-8')
    if len(src) > 200:          # Must not be longer than 255 chars.
        src = src[:197] + '...'
    src = src.replace(':', ';')
    return "py:L%s:%d:%s" % ("%d_%d" % (lno0, lno1), lno0, src)

def get_printable_location(pc, block, module, unit, excs, function): # ,ec
    opcode = rffi.r_ulong(block[pc])>>8
    name = optable.names[opcode]
    lno = raw_pc_location(function.sourcemap, rffi.r_long(pc))[2]
    return "pc=%d %s module=%s:%d" % (pc, name, module.repr().encode('utf-8'), lno)

rvmprof.register_code_object_class(Function, get_function_name)

def get_code(pc, block, frame):
    return frame.function

#def get_unique_id(next_instr, is_being_profiled, bytecode):
def get_unique_id(pc, block, module, unit, exc, function):
    return rvmprof.get_unique_id(function)

jitdriver = jit.JitDriver(
    greens=['pc', 'block', 'module', 'unit', 'excs', 'function'], #, 'ec'],
    reds=['frame'], # 'regv', 
    virtualizables = ['frame'],
    get_printable_location=get_printable_location,
    get_unique_id=get_unique_id, is_recursive=True)

@rvmprof.vmprof_execute_code("pypy", get_code, space.Object)
def interpret(pc, block, frame):
    function = jit.promote(frame.function)
    module = jit.promote(frame.module)
    unit   = jit.promote(frame.unit)
    excs   = jit.promote(frame.excs)
    try:
        while pc < len(block):
            try:
                jitdriver.jit_merge_point(
                    pc=pc, block=block, module=module, unit=unit, excs=excs,
                    function=function,
                    frame=frame) #ec=ec, regv=regv, 
                opcode = rffi.r_ulong(block[pc])>>8
                ix = pc+1
                pc = ix+(rffi.r_ulong(block[pc])&255)
                # Not sure..
                #if ec.debug_hook is not None:
                #    hook, ec.debug_hook = ec.debug_hook, None
                #    res = ec.debug_hook.call([DebugContext(rffi.r_long(ix), unit, frame)])
                #    if res != space.null:
                #        ec.debug_hook = res
                #print optable.dec[opcode][0]
                regv = frame # from now on..
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
                elif opcode == opcode_of('yield'):
                    result = regv.load(block[ix+0])
                    jit.hint(frame, force_virtualizable=True)
                    raise Yield(pc, result)
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
                    regv.store(block[ix+0], frame.load_local(block[ix+1]))
                elif opcode == opcode_of('setloc'):
                    value = regv.load(block[ix+2])
                    frame.store_local(block[ix+1], value)
                    regv.store(block[ix+0], value)
                elif opcode == opcode_of('getupv'):
                    value = get_upframe(frame, block[ix+1]).load_local(block[ix+2])
                    regv.store(block[ix+0], value)
                elif opcode == opcode_of('setupv'):
                    value = regv.load(block[ix+3])
                    get_upframe(frame, block[ix+1]).store_local(block[ix+2], value)
                    regv.store(block[ix+0], value)
                elif opcode == opcode_of('getglob'):
                    regv.store(block[ix+0],
                        module.getattr(get_string(unit, block, ix+1)))
                elif opcode == opcode_of('setglob'):
                    regv.store(block[ix+0],
                        module.setattr(
                            get_string(unit, block, ix+1),
                            regv.load(block[ix+2])))
                elif opcode == opcode_of('loglob'):
                    src_module = regv.load(block[ix+0])
                    assert isinstance(src_module, space.Module)
                    for name in src_module.list_locals():
                        if name in [u"dir", u"name", u"import"]: # TODO: Do something else that
                            continue                             #       makes sense
                        module.setattr(name, src_module.getattr(name))
                elif opcode == opcode_of('not'):
                    if space.is_false(regv.load(block[ix+1])):
                        regv.store(block[ix+0], space.true)
                    else:
                        regv.store(block[ix+0], space.false)
                elif opcode == opcode_of('isnull'):
                    if regv.load(block[ix+1]) is space.null:
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
                        frame.store(exc.reg, unwinder.exception)
                        pc = exc.label
                        #print "exception handler found"
                        break
                else:
                    raise
            except StopIteration as stop:
                # Doing an exception check to see if .next() was called in try block.
                unwinder = space.unwind(space.LUncatchedStopIteration())
                for exc in excs:
                    if exc.start < pc <= exc.stop:
                        frame.store(exc.reg, unwinder.exception)
                        pc = exc.label
                        break
                else:
                    raise unwinder
    except space.Unwinder as unwinder:
        unwinder.traceback.contents.append(TraceEntry(rffi.r_long(pc), unit.sources, frame.sourcemap, unit.path))
        raise
    except StackOverflow as overflow:
        raise space.unwind(space.LError(
            u"maximum recursion depth exceeded"))

    return space.null

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


#class DebugContext(space.Object):
#    def __init__(self, pc, unit, frame):
#        self.pc = pc
#        self.unit = unit
#        self.frame = frame
#
#@DebugContext.method(u"get_pc_location", space.signature(DebugContext))
#def DebugContext_get_pc_location(self):
#    entry = TraceEntry(self.pc, self.unit.sources, self.frame.sourcemap, self.unit.path)
#    loc, col0, lno0, col1, lno1 = entry.pc_location()
#    return space.List([loc,
#        space.Integer(col0), space.Integer(lno0),
#        space.Integer(col1), space.Integer(lno1)
#    ])

# The idea of introspection object is to support abstract interpretation of code.
class Introspection(space.Object):
    _immutable_fields_ = ["closure", "excs_l"]
    def __init__(self, closure):
        self.closure = closure
        self.excs_l = excs_introspection(closure.function.excs)

    def getattr(self, name):
        if name == u"closure":
            return self.closure
        elif name == u"is_generator":
            return space.boolean(self.closure.function.flags & 2 != 0)
        elif name == u"excs":
            return self.excs_l
        elif name == u"regc":
            return space.Integer(
                rffi.r_long(self.closure.function.regc))
        elif name == u"localc":
            return space.Integer(
                rffi.r_long(self.closure.function.localc))
        elif name == u"length":
            return space.Integer(len(self.closure.function.block))
        elif name == u"module":
            return self.closure.frame.module
        return space.Object.getattr(self, name)

    def getitem(self, index):
        pc = space.cast(index, space.Integer, u"[index]").value
        if pc < len(self.closure.function.block):
            return space.Integer(
                rffi.r_long(self.closure.function.block[pc]))
        raise space.OldError(u"pc out of range")

@Introspection.method(u"get_sourceloc", space.signature(Introspection, space.Integer))
def Introspection_get_source_location(self, pc):
    return sourceloc_introspection(
        int(pc.value), self.closure.function)

@Introspection.method(u"constant", space.signature(Introspection, space.Integer))
def Introspection_constant(self, ix1):
    unit = self.closure.function.unit
    if ix1.value < len(unit.constants):
        return unit.constants[ix1.value]
    raise space.OldError(u"Introspection.constant cannot succeed (opcode messup/corruption?)")

@Introspection.method(u"getupv", space.signature(Introspection, space.Integer, space.Integer))
def Introspection_getupv(self, ix1, ix2):
    frame = self.closure.frame # already the parent of 'current' function.
    for i in range(ix1.value):
        if frame:
            frame = frame.parent
    if frame and ix2.value < len(frame.local):
        return frame.local[rffi.r_ushort(ix2.value)]
    raise space.OldError(u"Introspection.getupv cannot succeed (opcode messup/corruption?)")

# The setupv and other intrusive actions are not provided here,
# because we are supposed to use this for analysis and abstract
# interpretation. Not for interpretation.
        
def excs_introspection(excs):
    out = []
    for exc in excs:
        o = space.Exnihilo()
        o.setattr(u"start",
            space.Integer(rffi.r_long(exc.start)))
        o.setattr(u"stop",
            space.Integer(rffi.r_long(exc.stop)))
        o.setattr(u"label",
            space.Integer(rffi.r_long(exc.label)))
        o.setattr(u"reg",
            space.Integer(rffi.r_long(exc.reg)))
        out.append(o)
    return space.List(out)

def sourceloc_introspection(pc, function):
    trace = TraceEntry(pc,
        function.unit.sources,
        function.sourcemap,
        function.unit.path)
    name, col0, lno0, col1, lno1 = trace.pc_location()
    start = space.Exnihilo()
    start.setattr(u"col", space.Integer(col0))
    start.setattr(u"lno", space.Integer(lno0))
    stop = space.Exnihilo()
    stop.setattr(u"col", space.Integer(col1))
    stop.setattr(u"lno", space.Integer(lno1))
    obj = space.Exnihilo()
    obj.setattr(u"source", name)
    obj.setattr(u"start", start)
    obj.setattr(u"stop", stop)
    return obj
