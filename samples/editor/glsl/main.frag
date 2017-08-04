#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

// This is going to be the "font fragment shader"
layout (location = 0) in vec3 color;
layout (location = 0) out vec4 frag_color;

void main(void)
{
    frag_color = vec4(color, 1.0);
}
