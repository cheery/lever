import re

source = [
    ('assert',   0x00, False, 'vreg'),
    ('except',   0x01, True,  'block'),
    ('constant', 0x10, True,  'constant'),
    ('list',     0x20, True,  'vreg*'),
    ('move',     0x30, False, 'vreg vreg'),
    ('call',     0x40, True,  'vreg vreg*'),
    ('not',      0x41, True, 'vreg'),
    ('contains', 0x42, True, 'vreg vreg'),
    ('return',   0x50, False, 'vreg'),
    ('jump',     0x60, False, 'block'),
    ('cond',     0x70, False, 'vreg block block'),
    ('func',     0x80, True,  'function'),
    ('iter',     0xC0, True,  'vreg'),
    #('next',     0xC1, True,  'vreg'),
    #('iterstop', 0xC2, False, 'block'),
    ('next',     0xC3, True,  'vreg block'),
    ('getattr',  0xD0, True,  'vreg string'),
    ('setattr',  0xD1, True,  'vreg string vreg'),
    ('getitem',  0xD2, True,  'vreg vreg'),
    ('setitem',  0xD3, True,  'vreg vreg vreg'),
    ('getloc',   0xE0, True,  'index'),
    ('setloc',   0xE1, True,  'index vreg'),
    ('getupv',   0xE2, True,  'index index'),
    ('setupv',   0xE3, True,  'index index vreg'),
    ('getglob',  0xF0, True,  'string'),
    ('setglob',  0xF1, True,  'string vreg'),
]

enc = {}
dec = {}
names = {}

for opname, opcode, has_result, form in source:
    assert opcode not in dec, opcode
    pattern = re.split(r"\s+", form.rstrip('*'))
    if form.endswith('*'):
        variadic = pattern.pop()
    else:
        variadic = None
    enc[opname] = opcode, has_result, pattern, variadic
    dec[opcode] = opname, has_result, pattern, variadic
    names[opcode] = opname
