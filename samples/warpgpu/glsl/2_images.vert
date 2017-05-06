#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec2 position;
layout (location = 0) out vec2 a_position;

void main(void)
{
    gl_Position = vec4(position, 0.0, 1.0);
    a_position = position;
}
