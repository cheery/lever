from bpy.types import Mesh
import bpy, bmesh, struct, json, sys, itertools, os

args = list(itertools.dropwhile(lambda x: x != "--", sys.argv))

outpath = os.path.abspath(args[1])
rel = lambda x: os.path.join(os.path.dirname(outpath), x)

meshes = []
for obj in bpy.data.objects:
    if isinstance(obj.data, Mesh):
        mesh = obj.to_mesh(bpy.context.scene, True, "RENDER")
        mesh.calc_normals_split()
        for polygon in mesh.polygons:
            assert polygon.loop_total == 3, ""
        meshes.append((obj, mesh))

if len(meshes) == 0:
    raise Exception("No mesh found")

vbo_path = os.path.splitext(os.path.basename(outpath))[0] + ".vbo"
header = {
    "vbo": vbo_path,
    # It is little bit of cheating to go so straight about this.
    "vertexBindingDescriptions": [{
        "binding": 0,
        "inputRate": "VERTEX",
        "stride": struct.calcsize('ffffff'),
    }],
    "vertexAttributeDescriptions": [
        dict( # position
            binding = 0, location = 0, format = "R32G32B32_SFLOAT", offset = 0
        ),
        dict( # normal
            binding = 0, location = 1, format = "R32G32B32_SFLOAT", offset = 4*3
        )
    ],
}

with open(outpath, "w") as fd:
    json.dump(header, fd)

with open(rel(header["vbo"]), "wb") as fd:
    for obj, mesh in meshes:
        for polygon in mesh.polygons:
            s = polygon.loop_start
            l = polygon.loop_total
            for i in range(s, s+l):
                vi = mesh.loops[i].vertex_index
                v = mesh.vertices[vi]
                n  = obj.matrix_world * mesh.loops[i].normal
                co = obj.matrix_world * v.co
                fd.write(struct.pack('ffffff', co.x, co.z, -co.y, n.x, n.z, -n.y))

sys.exit(0)
