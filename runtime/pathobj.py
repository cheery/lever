from rpython.rlib.objectmodel import compute_hash
from rpython.rlib.rarithmetic import intmask
from rpython.rlib import rstring
from space import *
import os
import sys

class Path(Object):
    _immutable_fields_ = ['prefix', 'pathseq[*]']
    def __init__(self, prefix, pathseq):
        self.prefix = prefix
        self.pathseq = pathseq

    def getattr(self, name):
        if name == u"basename":
            if len(self.pathseq) == 0:
                return String(u"")
            return String(self.pathseq[-1])
        if name == u"prefix":
            return self.prefix
        if name == u"dirname":
            pathseq = self.pathseq
            L = len(pathseq) - 1
            if L >= 0:
                return Path(self.prefix, pathseq[0:L])
            else:
                return self
        return Object.getattr(self, name)

    def eq(self, other):
        if isinstance(other, Path):
            return pathcmp(self, other) == 0
        return False

    def hash(self):
        value = 0x345678
        value = (1000003 * value) ^ self.prefix.hash()
        for item in self.pathseq:
            value = (1000003 * value) ^ compute_hash(item)
        value = value ^ len(self.pathseq)
        return intmask(value)

    def repr(self):
        return u"path(" + String(stringify(self)).repr() + u")"

@Path.method(u"relpath", signature(Path, Object, optional=1))
def Path_relpath(dst, rel):
    if rel:
        rel = abspath(to_path(rel))
    else:
        rel = getcwd()
    if isinstance(rel.prefix, PosixPrefix) and isinstance(dst.prefix, PosixPrefix):
        if dst.prefix.label != rel.prefix.label and dst.prefix.label != u"":
            return dst
        dst = concat(rel, dst)
        C = min(len(dst.pathseq), len(rel.pathseq))
        for i in range(C):
            if dst.pathseq[i] != rel.pathseq[i]:
                C = i
                break
        result = []
        if rel.pathseq[C] != u"": # Avoids adding the ".." if the rel ended with a slash.
            for n in range(C, len(rel.pathseq)):
                result.append(u"..")
        for m in range(C, len(dst.pathseq)):
            result.append(dst.pathseq[m])
        return Path(PosixPrefix(u"", False), result[:])
    elif isinstance(rel.prefix, PosixPrefix) and isinstance(dst.prefix, URLPrefix):
        return dst
    else:
        raise unwind(LError(u"Path_relpath: missing feature, file an issue or implement"))

@Path.method(u"drop", signature(Path, Integer))
def Path_drop(self, count):
    pathseq = self.pathseq
    L = len(pathseq) - max(0, count.value)
    if L > 0:
        return Path(self.prefix, pathseq[0:L])
    elif len(pathseq) > 0:
        return Path(self.prefix, [])
    else:
        return self

@Path.method(u"get_os_path", signature(Path))
def Path_get_os_path(self):
    return String(os_stringify(self))

@Path.method(u"to_string", signature(Path))
def Path_to_string(self):
    return String(stringify(self))

@Path.instantiator
@signature(Object)
def _(obj):
    if isinstance(obj, String):
        return parse(obj.string)
    elif isinstance(obj, Path):
        return obj
    raise OldError(u"path() expected string or path object.")

@operators.ne.multimethod_s(Path, Path)
def pathcmp_eq(a, b):
    k = pathcmp(a, b)
    return boolean(k != 0)

@operators.eq.multimethod_s(Path, Path)
def pathcmp_eq(a, b):
    k = pathcmp(a, b)
    return boolean(k == 0)

@operators.lt.multimethod_s(Path, Path)
def pathcmp_lt(a, b):
    k = pathcmp(a, b)
    return boolean(k == 1)

@operators.gt.multimethod_s(Path, Path)
def pathcmp_gt(a, b):
    k = pathcmp(a, b)
    return boolean(k == 2)

@operators.le.multimethod_s(Path, Path)
def pathcmp_le(a, b):
    k = pathcmp(a, b)
    return boolean(k == 1 or k == 0)

@operators.ge.multimethod_s(Path, Path)
def pathcmp_ge(a, b):
    k = pathcmp(a, b)
    return boolean(k == 2 or k == 0)

def pathcmp(a, b):
    if not prefix_eq(a.prefix, b.prefix):
        return -1 # not eq.
    m = len(a.pathseq)
    n = len(b.pathseq)
    l = min(m, n)
    for i in range(0, l):
        if a.pathseq[i] == u"" and b.pathseq[i] == u"":
            return 0
        if a.pathseq[i] == u"":
            return 1
        if b.pathseq[i] == u"":
            return 2
        if a.pathseq[i] != b.pathseq[i]:
            break
    else:
        if m == n:
            return 0 # eq.
        elif m < n:
            return 1 # lt.
        elif m > n:
            return 2 # gt.
    return -1 # not eq.

def prefix_eq(a, b):
    if isinstance(a, PosixPrefix) and isinstance(b, PosixPrefix):
        return a.label == b.label and a.is_absolute == b.is_absolute
    if isinstance(a, URLPrefix) and isinstance(b, URLPrefix):
        return a.protocol == b.protocol and a.domain == b.domain
    return False

class Prefix(Object):
    _immutable_fields_ = ['label', 'is_absolute', 'protocol', 'domain']

class PosixPrefix(Prefix):
    _immutable_fields_ = ['label', 'is_absolute']
    def __init__(self, label, is_absolute):
        self.label = label
        self.is_absolute = is_absolute

    def getattr(self, name):
        if name == u"is_absolute":
            return boolean(self.is_absolute)
        if name == u"label":
            return String(self.label)
        return Object.getattr(self, name)

    def hash(self):
        value = 0x345678
        value = (1000003 * value) ^ compute_hash(self.label)
        value = (1000003 * value) ^ compute_hash(self.is_absolute)
        return intmask(value)

    def eq(self, other):
        return prefix_eq(self, other)

class URLPrefix(Prefix):
    _immutable_fields_ = ['protocol', 'domain']
    def __init__(self, protocol, domain):
        self.protocol = protocol
        self.domain = domain

    def getattr(self, name):
        if name == u"protocol":
            return String(self.protocol)
        if name == u"domain":
            return String(self.domain)
        return Object.getattr(self, name)

    def hash(self):
        value = 0x345678
        value = (1000003 * value) ^ compute_hash(self.protocol)
        value = (1000003 * value) ^ compute_hash(self.domain)
        return intmask(value)

    def eq(self, other):
        return prefix_eq(self, other)

@PosixPrefix.instantiator
def _(argv):
    obj = PosixPrefix(u"", False)
    if len(argv) >= 1:
        obj.setattr(u"label", argv[0])
    if len(argv) >= 2:
        obj.setattr(u"is_absolute", argv[1])
    return obj

@URLPrefix.instantiator
def _(argv):
    obj = URLPrefix(u"", u"")
    if len(argv) >= 1:
        obj.setattr(u"domain", argv[0])
    if len(argv) >= 2:
        obj.setattr(u"protocol", argv[1])
    return obj

# The following generic path parsing function handles both unix and nt paths along URLs.
def parse(string, nt=False):
    prefix = None
    pathseq = []
    buf = []
    state = 0
    ch = u""
    for ch in string:
        slash = (ch == u"/" or (nt and ch == u"\\"))
        # state == 0: {label, protocol, name}
        if state == 0: 
            if slash:
                state = 4 # Potential absolute path.
            elif ch == u":":
                state = 2 # there is a label in the buffer.
            else:
                buf.append(ch)
                state = 1
        # state == 1: {label, protocol, name}
        elif state == 1:
            if slash:
                name, buf = u''.join(buf), []
                pathseq.append(name)
                prefix = PosixPrefix(u"", False)
                state = 8 # ordinary path.
            elif ch == u":":
                state = 2 # there is a label in the buffer.
            else:
                buf.append(ch)
        # state == 2: labelled {label, name}
        elif state == 2:
            if slash:
                state = 4 # Potential absolute path.
            else:
                label, buf = u''.join(buf), []
                prefix = PosixPrefix(label, is_absolute=False)
                state = 8 # ordinary path.
                buf.append(ch)
        # state == 4: potential absolute path {label, protocol}
        #             backslash, nt-absolute or nt-UNC path. {protocol}
        elif state == 4:
            if slash:
                protocol, buf = u''.join(buf), []
                prefix = URLPrefix(protocol, u"")
                if ch == u"/": # ensure nobody makes getcwd return backslashed URLs.
                    nt = False  # and that backslashes aren't interpreted in URLs.
                state = 6 # Starts collecting domain segment.
            else:
                label, buf = u''.join(buf), []
                prefix = PosixPrefix(label, is_absolute=True)
                state = 8 # ordinary path.
                buf.append(ch)
        # state == 6: URL or nt-UNC {domain}
        elif state == 6:
            if slash and isinstance(prefix, URLPrefix):
                domain, buf = u''.join(buf), []
                prefix.domain = domain
                state = 8 # ordinary path.
            elif slash:
                raise OldError(u"path parser state corruption")
            else:
                buf.append(ch)
        # state == 8: uniform path. {name}
        elif state == 8:
            if slash:
                name, buf = u''.join(buf), []
                pathseq.append(name)
                state = 8 # ordinary path.
            else:
                buf.append(ch)
        else:
            raise OldError(u"path parser state corruption")
    if state == 0:
        prefix = PosixPrefix(u"", is_absolute=False)
    elif state == 1:
        prefix = PosixPrefix(u"", is_absolute=False)
        pathseq.append(u''.join(buf))
    elif state == 2:
        label, buf = u''.join(buf), []
        prefix = PosixPrefix(label, is_absolute=False)
    elif state == 4:
        label, buf = u''.join(buf), []
        prefix = PosixPrefix(label, is_absolute=True)
        pathseq.append(u''.join(buf))
    elif state == 6 and isinstance(prefix, URLPrefix):
        domain, buf = u''.join(buf), []
        prefix.domain = domain
    elif state == 8 and isinstance(prefix, Prefix):
        pathseq.append(u''.join(buf))
    else:
        raise OldError(u"path parser state corruption")
    return Path(prefix, pathseq_ncat([], pathseq))

@operators.concat.multimethod_s(String, Path)
def _(a, b):
    return concat(parse(a.string), b)

@operators.concat.multimethod_s(Path, String)
def _(a, b):
    return concat(a, parse(b.string))

@operators.concat.multimethod_s(Path, Path)
def concat(a, b):
    if is_absolute(b):
        return b
    assert isinstance(a, Path), "concat lhs not a path"
    assert isinstance(b, Path), "concat rhs not a path"
    pathseq = pathseq_ncat(list(a.pathseq), list(b.pathseq))
    return Path(a.prefix, pathseq)

def pathseq_ncat(pathseq, tail):
    if len(pathseq) > 0 and pathseq[-1] == u"":
        pathseq.pop()
    slash = False
    for name in tail:
        slash = False
        if name == u"" or name == u".":
            slash = True
            continue
        if name == u".." and len(pathseq) > 0 and pathseq[-1] != u"..":
            pathseq.pop()
        else:
            pathseq.append(name)
    if slash:
        pathseq.append(u"")
    return pathseq[:]

def is_absolute(pathobj):
    prefix = pathobj.prefix
    if isinstance(prefix, PosixPrefix):
        return prefix.is_absolute
    return True

def stringify(path, nt=False):
    path = to_path(path)
    prefix = path.prefix
    pathseq = list(path.pathseq)
    if isinstance(prefix, URLPrefix):
        string = prefix.protocol
        if len(string) > 0:
            string += u":"
        if nt and string == u"":             # Turns //name/ to NT UNC path.
            string += ur"\\" + prefix.domain # I am not sure if this is the
            if len(pathseq) == 0:            # correct action.
                pathseq.append(u"") # Adds a slash.
        else:
            string += ur"//" + prefix.domain
        pathseq.insert(0, string)
    elif isinstance(prefix, PosixPrefix):
        if prefix.is_absolute:
            if len(pathseq) == 0:   # Ensures a slash is produced
                pathseq.append(u"")
            pathseq.insert(0, u"")
        elif len(pathseq) > 0 and pathseq[0].count(u":") > 0: # Makes sure the first
            pathseq.insert(0, u".")                           # item not recognized as
        elif len(pathseq) > 0 and len(pathseq[0]) == 0:       # posix label.
            pathseq.insert(0, u".")                           # rest of this ensures
        elif len(path.pathseq) == 0:                          # that we get "."
            pathseq.insert(0, u".")                           # produced in any case.
        # The above cases ensure that this way of adding the prefix
        # can be actually correct.
        if prefix.label != u"":
            pathseq[0] = prefix.label + u":" + pathseq[0]
    else:
        raise OldError(u"custom prefix passed to stringification [corruption]")
    if nt:
        for name in pathseq:
            if name.count(u"\\") > 0:
                raise OldError(ur"nt_stringify cannot stringify file/directory names that contain '\\'")
    string = (u"\\" if nt else u"/").join(pathseq)
    return rstring.assert_str0(string)

def getcwd():
    return os_parse(os.getcwd().decode('utf-8'))

def chdir(path):
    os.chdir(os_stringify(path).encode('utf-8'))

@cast_for(Path)
def to_path(obj):
    if isinstance(obj, String):
        return parse(obj.string)
    elif isinstance(obj, Path):
        return obj
    else:
        raise OldError(u"expected path")

def directory(path):
    return path.getattr(u'dirname')

def abspath(path):
    if is_absolute(path):
        return path
    return concat(getcwd(), path)

# nt stands for "non-technology"
nt_parse = lambda string: parse(string, nt=True)
nt_stringify = lambda path: stringify(path, nt=True)

if sys.platform == "win32":
    os_parse = nt_parse
    os_stringify = nt_stringify
else:
    os_parse = parse
    os_stringify = stringify
