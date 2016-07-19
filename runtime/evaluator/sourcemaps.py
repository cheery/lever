from rpython.rtyper.lltypesystem import rffi
import space

# TODO: Without the path, this doesn't really pinpoint the origin of a traceback entry.
# TODO: Without pc=0 entry in sourcemap CallError will return the wrong line.
class TraceEntry(space.Object):
    def __init__(self, pc, sources, sourcemap, path=space.null):
        self.pc = pc
        self.sources = sources
        self.sourcemap = sourcemap
        self.path = path

    def pc_location(self):
        pc = self.pc
        sources = self.sources
        sourcemap = self.sourcemap
        if not isinstance(sourcemap, space.Uint8Array):
            return space.String(u"<no sourcemap>"), 0, 0, -1, -1
        i = 0
        while i < sourcemap.length:
            i, count = dec_vlq(sourcemap, i)
            i, file_id = dec_vlq(sourcemap, i)
            i, col0 = dec_vlq(sourcemap, i)
            i, lno0 = dec_vlq(sourcemap, i)
            i, col1 = dec_vlq(sourcemap, i)
            i, lno1 = dec_vlq(sourcemap, i)
            if pc <= count and file_id < len(sources):
                return sources[file_id], col0, lno0, col1, lno1
            else:
                pc -= count
        return space.String(u"<over sourcemap>"), 0, 0, -1, -1

def dec_vlq(sourcemap, i):
    i, ubyte = nextbyte(sourcemap, i)
    output = 0
    while ubyte & 0x80:
        output |= ubyte & 0x7F
        output <<= 7
        i, ubyte = nextbyte(sourcemap, i)
    output |= ubyte
    return i, output

def nextbyte(sourcemap, i):
    if i < sourcemap.length:
        return i+1, rffi.r_long(sourcemap.uint8data[i])
    return i, 0

def getitem_int(cell, index):
    item = cell.getitem(space.Integer(index))
    if isinstance(item, space.Integer):
        return item.value
    raise space.OldError(u"invalid sourcemap format")
