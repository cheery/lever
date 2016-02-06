#version 420

uniform vec3 color;
in vec3 frag_normal;
layout(location = 0) out vec4 frag_color;

#define pi 3.1415926535897

void main (void)  
{     
    vec3 normal = normalize(frag_normal);
    float shade = 0.5*(1.0 + dot(normal, normalize(vec3(0.1, 0.2, 0.1))));
    frag_color = vec4(color, 1.0) * shade;
}
