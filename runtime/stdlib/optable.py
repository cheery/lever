from evaluator import optable
from space import *

enc = Dict()
dec = Dict()

for opname, (opcode, has_result, pattern, variadic) in optable.enc.items():
    opname = from_cstring(opname)
    opcode = Integer(opcode)
    has_result = boolean(has_result)
    pattern = List([from_cstring(pat) for pat in pattern])
    if variadic is not None:
        variadic = from_cstring(variadic)
    else:
        variadic = null
    enc.setitem(opname, List([opcode, has_result, pattern, variadic]))
    dec.setitem(opcode, List([opname, has_result, pattern, variadic]))

module = Module(u'optable', {
    u"enc": enc,
    u"dec": dec,
}, frozen=True)
