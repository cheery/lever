#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec4 normal;

layout (location = 0) out vec4 frag_color;

float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void main(void)
{
    float noise = rand(gl_FragCoord.xy) * 0.01;
    float shade = noise + abs(0.5 * dot(vec3(0, 1, 0), normalize(normal.xyz)) + 0.1);
    frag_color = vec4(shade*0.01, shade*0.23, shade*0.01, 1.0);
}
