from objects.core import *
from objects.modules import Module

# Add instruction name here, then write its value below
# and it goes into all the other tables from here.
groups = ["simple", "branch", "frame", "branchx",
          "guard",  "ionly",  "oonly", "terminal"]
opcodes = [
    'is_true', 'eq', 'match', 'next', 'move', 'global', 'attr', 'item',
    'true', 'false', 'call', 'raise', 'yield', 'yield_from', 'deref' ]
__all__ = ['o_'+code for code in groups + opcodes]

# The instruction set for clauses.
o_simple   = 0x0 # Group of simple instructions.
o_branch   = 0x1 # With a procedure index to identify branch target.
o_frame    = 0x2 # With a bitmask telling which closures are not inserted into frame.
                 # closures*, inputs*, outputs*
o_branchx  = 0x3 # With procedure index, failure_path, inputs*, outputs[T]*
o_guard    = 0x4 # Boolean guards. With a count telling where terminal is.
                 # Terminal position counted forwards from next instruction.

o_ionly    = 0x5 # Inputs-only instructions.
o_oonly    = 0x6 # Outputs-only instructions.
o_terminal = 0x7 # Terminal for guards.
                 # outputs[F]*     

# The guards
o_is_true = (0x0 << 3) | 0x4 # failure_path, inputs*, outputs[T]*
o_eq      = (0x1 << 3) | 0x4 
o_match   = (0x2 << 3) | 0x4 
o_next    = (0x3 << 3) | 0x4 

# Basic abstract instructions
o_move   = (0x0 << 3) # inputs*, outputs*
o_global = (0x1 << 3)
o_attr   = (0x2 << 3)
o_item   = (0x3 << 3)

o_true   = (0x4 << 3)
o_false  = (0x5 << 3)
o_call   = (0x6 << 3)

# Inputs-only instructions.
o_raise      = (0x8 << 3) | 0x5 # inputs*
o_yield      = (0x9 << 3) | 0x5
o_yield_from = (0xA << 3) | 0x5

# Basic abstract instructions (extended)
o_deref   = (0xC << 3)

# This is the module you get by importing 'vmoptable'
module = Module()

atoms = dict((name, Atom(0)) for name in groups + opcodes)
for name, atom in atoms.iteritems():
    set_attribute(module, wrap('o_'+name), atom)
name_to_code = dict((name[2:], value)
    for name, value in globals().iteritems() if name.startswith('o_'))

set_attribute(module, wrap(u"groups"), ImmutableList([
    Tuple([wrap(name), atoms[name], wrap(name_to_code[name])])
    for name in groups]))

set_attribute(module, wrap(u"opcodes"), ImmutableList([
    Tuple([wrap(name), atoms[name], wrap(name_to_code[name])])
    for name in opcodes]))
