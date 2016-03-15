#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec4 color;

layout (location = 0) out vec4 frag_color;

void main(void)
{
    if (length(gl_PointCoord * 2.0 - 1.0) > 1.0) {
        discard;
    }
    frag_color = color;
}
