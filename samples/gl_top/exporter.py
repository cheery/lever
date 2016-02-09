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

vbo_path = os.path.splitext(os.path.basename(outpath))[0] + ".vbo"
header = {
    "vbo": vbo_path,
    "stride": struct.calcsize('ffffff'),
    "format": {
        "position": {"offset": 0,   "type": "float", "size": 3, "normalized":False},
        "normal":   {"offset": 4*3, "type": "float", "size": 3, "normalized":False}
    }
}

mesh.calc_normals_split()
for polygon in mesh.polygons:
    assert polygon.loop_total == 3, ""

with open(outpath, "w") as fd:
    json.dump(header, fd)

with open(rel(header["vbo"]), "wb") as fd:
    for polygon in mesh.polygons:
        s = polygon.loop_start
        l = polygon.loop_total
        for i in range(s, s+l):
            vi = mesh.loops[i].vertex_index
            v = mesh.vertices[vi]
            n = mesh.loops[i].normal
            fd.write(struct.pack('ffffff', v.co.x, v.co.z, -v.co.y, n.x, n.z, -n.y))

sys.exit(0)
