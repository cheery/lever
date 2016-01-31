#version 420

in vec3 position;
in vec3 normal;
uniform float time;
uniform mat4 invprojection;
uniform mat4 projection;
uniform mat4 modelview;
uniform vec3 org;
out vec3 frag_normal;
out vec3 frag_raydir;

void main(void)
{
    vec4 point = modelview * vec4(position, 1.0);
    gl_Position = projection * point;
    frag_normal = mat3(modelview) * normal;
    frag_raydir = point.xyz - org;
}
