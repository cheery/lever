#version 420

in vec3 frag_color;
layout(location = 0) out vec4 color;

void main(void)
{
    color = vec4(frag_color, 1.0);
}
