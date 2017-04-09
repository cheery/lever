#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec4 color;

layout (location = 0) out vec4 frag_color;

layout (binding = 1) uniform sampler2D texSampler;

void main(void)
{
    frag_color = texture(texSampler, color.xy);
}
