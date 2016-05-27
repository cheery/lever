def test():
    import sys
    import space
    import loader
    import bincode.encoder
    import base
    bincode.encoder.dump_function('sample.lic',
        functions=[
            (0x0, 32, 0, 0, [
                0xF002, 0x0, 0x0,
                0x1002, 0x1, 0x1,
                0x1002, 0x2, 0x2,
                0x4005, 0x0, 0x0, 0x0, 0x1, 0x2,
                0x5001, 0x0,
            ])],
        constants=[
            "print",
            15,
            1.2,
            ])
    program = loader.from_file(sys.argv[1])
    module = space.Module(u'main', {}, extends=base.module)
    print program.call([module]).repr()

# encoders = {}
# decoders = {}
# 
# def prepare(opname, opcode, has_result, pattern, variadic):
#     if has_result:
#         pattern = ['dreg'] + pattern
#     def _encoder_(*argv):
#         assert len(argv) < 256
#         if variadic:
#             assert len(argv) >= len(pattern)-1
#         else:
#             assert len(argv) == len(pattern), pattern
#         op = [opcode << 8 | len(argv)]
#         for arg in argv:
#             assert isinstance(arg, int) and 0 <= arg < 1<<16
#             op.append(arg)
#         return op
#     encoders[opname] = _encoder_
#     def _decoder_(block, pc):
#         opcode = block[pc] >> 8
#         oplen = (block[pc] & 255)
#         if variadic:
#             assert oplen >= len(pattern)-1
#             argc = oplen
#             patv = pattern[:-2] + [pattern[-1]] * (argc-len(pattern)+1)
#         else:
#             argc = len(pattern)
#             patv = pattern
#         return pc+1+oplen, opname, zip(patv, block[pc+1:pc+1+argc])
#     decoders[opcode] = _decoder_
# 
# for args in itab:
#     prepare(*args)
# 
# block = (
#     encoders['constant'](1, 0) +
#     encoders['constant'](2, 1) +
#     encoders['constant'](3, 2) +
#     encoders['call'](1, 2, 3) +
#     encoders['return'](1))
# 
# pc = 0
# while pc < len(block):
#     pcl = pc
#     pc, name, args = decoders[block[pc] >> 8](block, pc)
#     pattern = ' '.join(map("{:04x}".format, block[pcl:pc]))
#     print "{:<30} {:>10} {}".format(pattern, name, args)
