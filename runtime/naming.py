# The way Lever modules are created do not leave a name
# for the module, it has to be resolved from the module
# where the function was defined in.
from space import *
from time import time

# TODO: Consider the options of giving the DocRef to builtins.
#       Also consider the option of how the name is retrieved
#       in...
# runtime/space/builtin.py:73
# runtime/module_resolution.py:135
# runtime/main.py:32

def get_name(obj, stale=1.0):
    doc = obj.getattr(u"doc")
    if not isinstance(doc, DocRef):
        return None
    base = doc.module
    stack = []
    while doc is not None:
        stack.append(doc)
        doc = doc.parent

    for doc in reversed(stack):
        if doc.name:
            base = base.getattr_or(doc.name.string, null)
        else:
            base = null

    if base is not obj:
        version_stamp = time()
        if doc.version + stale <= version_stamp:
            breath_first_search(doc.module, version_stamp)
            doc.version = version_stamp
            stack = []
            while doc is not None:
                stack.append(doc)
                doc = doc.parent
    
    name = []
    for doc in reversed(stack):
        if doc.name:
            name.append(doc.name.string)
        else:
            return None
    return u".".join(name)

def breath_first_search(module, version):
    queue = [(module, None)]
    while len(queue) > 0:
        item, parent = queue.pop()
        listing = item.listattr()
        for name in listing:
            name = cast(name, String, u"get_name")

            field = item.getattr(name.string)
            doc = field.getattr_or(u"doc", null)

            if doc == null:
                try: # TODO: remove Hax
                    field.getattr(u"doc") # Prevents setattr on fields we rather would not setattr ourselves.
                except space.Unwinder as unwind:
                    continue
                if isinstance(field, Module): # Another one we do not want to setattr.
                    continue
                # We used to do postorder traverse as post-import operation
                # We may want to remove the filling of null doc objects eventually.
                doc = DocRef(module, name, parent)
                doc.version = version
                try:
                    field.setattr(u"doc", doc)
                except space.Unwinder as unwind: # Not entirely nice.
                    continue
                queue.append((field, doc))
            elif not isinstance(doc, DocRef):
                continue
            elif doc.module is not module: # This rule may cause some nondeterminism
                continue                   # on how the module object is named.
                                           # we may work around this by requiring the
                                           # user to name all the objects with docrefs.
            elif doc.version == version: # Already visited
                continue
            else:
                doc.version = version
                doc.parent = parent
                doc.name = name
                queue.append((field, doc))

class DocRef(Object):
    def __init__(self, module, name=None, parent=None):
        self.module = module
        self.name = name
        self.parent = parent
        self.version = 0.0 # Allows the breath-first search above to proceed
                           # without an explicit set of visited docrefs.

        # TODO: Consider turning the version into a global timestamp,
        #       which is checked on regular intervals.
        # Then only when the timestamp is stale (older than 1sec)
        # the DocRef is attempted to be updated.
    
    def getattr(self, name):
        if name == u"module":
            return self.module
        elif name == u"name":
            if self.name is not None:
                return self.name
            else:
                return null
        elif name == u"parent":
            if self.parent is not None:
                return self.parent
            else:
                return null
        return Object.getattr(self, name)

    def listattr(self):
        listing = Object.listattr(self)
        listing.append(space.String(u"module"))
        listing.append(space.String(u"name"))
        listing.append(space.String(u"parent"))
        return listing

@DocRef.instantiator2(signature(Object, String, DocRef, optional=2))
def DocRef_init(module, name, parent):
    if parent and module is not parent.module:
        raise unwind(LError(u"DocRef.parent.module must match DocRef.module"))
    return DocRef(module, name, parent)
