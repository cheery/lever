#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec3 position;
layout (location = 1) in vec3 color;

layout (binding = 0) uniform testbuffer
{
    mat4 projection;
    mat4 modelview;
};

layout (location = 0) out vec4 out_color;

void main(void)
{
    out_color = vec4(color, 1.0);
    gl_Position = projection * modelview * vec4(position, 1.0);
    gl_Position *= vec4(1.0, -1.0, 1.0, 1.0);
}
