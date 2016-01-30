#version 420
precision mediump float;

in vec3 position;

uniform mat4 invprojection;
out vec3 fragRayDir;

void main(void)
{
    vec2 viewpoint = position.xy;
    gl_Position = vec4(position, 1.0);
    fragRayDir = (invprojection * vec4(viewpoint, -1.0, 1.0)).xyz;
}

