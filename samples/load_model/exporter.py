from bpy.types import Mesh
import bpy, bmesh, struct, json, sys, itertools, os

print(sys.argv)
args = list(itertools.dropwhile(lambda x: x != "--", sys.argv))

outpath = os.path.abspath(args[1])
rel = lambda x: os.path.join(os.path.dirname(outpath), x)

for obj in bpy.data.objects:
    if isinstance(obj.data, Mesh):
        mesh = obj.to_mesh(bpy.context.scene, True, "RENDER")
        break
else:
    raise Exception("No mesh found")

header = {
    "vbo": "test.vbo",
    "stride": struct.calcsize('fff'),
    "format": {
        "position": {"offset": 0, "type": "float", "size": 3, "normalized":False}
    }
}

for polygon in mesh.polygons:
    l = polygon.loop_total
    assert l == 3, "polygon count %s" % l
        
with open(outpath, "w") as fd:
    json.dump(header, fd)

with open(rel(header["vbo"]), "wb") as fd:
    for polygon in mesh.polygons:
        s = polygon.loop_start
        l = polygon.loop_total
        for i in range(s, s+l):
            vi = mesh.loops[i].vertex_index
            v = mesh.vertices[vi]
            fd.write(struct.pack('fff', v.co.x, v.co.z, -v.co.y))

sys.exit(0)
