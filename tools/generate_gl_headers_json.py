from bs4 import BeautifulSoup, NavigableString
import re
import json
import sys

if len(sys.argv) != 2:
    sys.stderr.write("usage: {} path/to/gl.xml\n".format(sys.argv[0]))
    sys.stderr.write("gl.xml can be found in the khronos.org registry\n")
    sys.exit(1)

with open(sys.argv[1]) as fd:
    soup = BeautifulSoup(fd.read(), 'xml')

def in_gl_api(node):
    if node.has_attr('api') and node["api"] != 'gl':
        return False
    if node.parent is not None:
        return in_gl_api(node.parent)
    return True

def get_tag(node):
    if isinstance(node, NavigableString):
        return ''
    return node.name

def rename(name):
    name = re.sub(' ', '', name)
    name = re.sub('^GLboolean', 'GLubyte', name)
    name = re.sub('^GLsizei', 'GLint', name)
    name = re.sub('^GLenum', 'GLint', name)
    name = re.sub('^GLcharARB', 'GLchar', name)
    name = re.sub('^GLintARB', 'GLint', name)
    name = re.sub('^GLclampf', 'GLfloat', name)
    name = re.sub('^GLclampd', 'GLdouble', name)
    name = re.sub('^GLclampx', 'GLint', name)
    name = re.sub('^GLbitfield', 'GLint', name)
    name = re.sub('^GLintptr', 'GLint', name)
    name = re.sub('^GLsizeiptr', 'GLint', name)
    name = re.sub('^GLint64', 'GLi64', name)
    name = re.sub('^GLuint64', 'GLu64', name)
    name = re.sub('^GLhandleARB', 'GLuint', name)
    if name.startswith('GL_'):
        return re.sub('^GL_', '', name)
    if name.startswith('GL'):
        return re.sub('^GL', '', name)
    if name.startswith('gl'):
        return re.sub('^gl(.)', lambda m: m.group(1).lower(), name)
    if name in ('void', 'void*', 'void**'):
        return name 
    if name == 'struct_cl_context*': # it's likely that these should be imported
        return 'void*'               # or just handled like this.
    if name == 'struct_cl_event*':
        return 'void*'              
    raise Exception("name of GL?: {!r}".format(name))

constants = {}
variables = {}

for en in soup.find_all('enum', value=True):
    if not in_gl_api(en):
        continue
    name = rename(en["name"])
    value = en["value"]
    assert name not in constants, name
    constants[name] = int(value, 16 if value.startswith('0x') else 10)

for proto in soup.find_all('proto'):
    if not in_gl_api(proto):
        continue
    restype_chain = list(proto.children)
    cname = restype_chain.pop(-1).string.strip()
    restype = rename(''.join(n.string.strip() for n in restype_chain if n.string.strip() != 'const'))
    argtypes = []
    for param in proto.parent.find_all('param'):
        pat1 = re.match(r"^(.+?)([a-zA-Z_0-9]+)\[[0-9]+\]$", param.text)
        pat2 = re.match("^(.+?)([a-zA-Z_0-9]+)$", param.text)
        if pat1:
            ctype = pat1.group(1)
            ptype = re.sub('const| ', '', ctype.strip()) + '*'
        else:
            assert pat2, param.text
            ctype = pat2.group(1)
            ptype = re.sub('const| ', '', ctype.strip())
        argtypes.append(ptype)
    argtypes = map(rename, argtypes)

    name = rename(cname)
    assert name not in variables, name
    variables[name] = {
        'name':cname,
        'type':{'type':'cfunc', 'restype':restype, 'argtypes':argtypes}}

assert len(variables['bufferData']['type']['argtypes']) == 4

print json.dumps(
    {'constants': constants, 'types':{}, 'variables':variables},
    indent = 4,
    sort_keys=True)
