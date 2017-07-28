#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec3 position;
layout (location = 1) in vec3 coord;
layout (location = 2) in vec3 color;

layout (location = 0) out vec3 out_coord;
layout (location = 1) out vec3 out_color;

void main(void)
{
    out_coord = coord;
    out_color = color;
    gl_Position = vec4(position, 1.0);
    gl_Position *= vec4(1.0, -1.0, 1.0, 1.0);
}
