from rpython.rlib.rthread import ThreadLocalReference
from objects.common import ModuleCell
from objects import *

# The coeffects are main element in why we already have
# an execution context.
class ExecutionContext:
    def __init__(self, coeffects):
        self.coeffects = coeffects

class GlobalState:
    ec = ThreadLocalReference(ExecutionContext,
        loop_invariant=True)

global_state = GlobalState()

def init_executioncontext(*args):
    ec = ExecutionContext(*args)
    global_state.ec.set(ec)

def get_ec():
    ec = global_state.ec.get()
    if isinstance(ec, ExecutionContext):
        return ec
    assert False, "threads don't support get_ec now."

# The coeffects are a bit like dynamic scope variables,
# except that they are indexed by a label rather than
# by a name.
def get_coeffect(face):
    ec = get_ec()
    try:
        return ec.coeffects[face]
    except KeyError:
        raise error(e_TypeError())

@builtin()
def w_call_with_coeffects(fn, coeffects):
    ec = get_ec()
    call_coeffects = ec.coeffects.copy()
    it = cast(call(op_iter, [coeffects]), Iterator)
    while True:
        try:
            x, it = it.next()
            tup = cast(x, Tuple).tuple_val
            if len(tup) != 2:
                raise error(e_TypeError())
            coeffect, obj = tup
        except StopIteration:
            break
        call_coeffects[coeffect] = obj
    previous = ec.coeffects
    ec.coeffects = call_coeffects
    try:
        result = callv(fn, [])
    finally:
        ec.coeffects = previous
    return Tuple(result)

# You're suppposed to access the coeffects through
# modules. Main advantage here is that you can
# abstract global mutable state into manageable elements.
class CoeffectModuleCell(ModuleCell):
    def __init__(self, coeffect, name, mutable):
        self.coeffect = coeffect
        self.name = name
        self.mutable = mutable

    def load(self):
        cf = get_coeffect(self.coeffect)
        return call(cf.face().getattr(self.name), [cf])

    def store(self, value):
        if not self.mutable:
            raise error(e_TypeError())
        cf = get_coeffect(self.coeffect)
        call(cf.face().setattr(self.name), [cf, value], 0)

class Coeffect(Object):
    def __init__(self):
        self.names = {}

def construct_coeffect(fields, module):
    coeffect = Coeffect()
    for name, mutable in fields:
        coeffect.names[name] = mutable 
        module.assign_cell(name,
            CoeffectModuleCell(coeffect, name, mutable))
    return coeffect
