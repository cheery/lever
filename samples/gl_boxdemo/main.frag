#version 420

uniform vec4 env_color;
uniform vec4 diffuse_color;
uniform vec2 resolution;
uniform float time;
uniform samplerCube texture0;
in vec3 frag_normal;
in vec3 frag_raydir;
layout(location = 0) out vec4 color;

#define pi 3.1415926535897

float rand(vec2 co){
    return fract(sin(dot(co.xy ,vec2(12.9898,78.233))) * 43758.5453);
}

void main (void)  
{     
    vec3 normal = normalize(frag_normal);
    vec2 uv = gl_FragCoord.xy / resolution.xy; 
     
    float cx = uv.x+0.5*sin(time/5.0); 
    float cy = uv.y+0.5*cos(time/3.0); 
     
    float v = sin(sqrt(100.0*(cx*cx+cy*cy))); 
    v += sin(uv.x*10.0+time); 
    v += cos(uv.y*4.0+time); 

    vec4 mirror = texture(texture0, reflect(normalize(frag_raydir), normal));
     
    float shade = dot(vec3(0.0, 1.0, 0.0), normal) * 0.5 + 0.5;
    vec4 env = env_color * (0.05 + 0.05 * rand(gl_FragCoord.xy+time));
    color = (diffuse_color * shade + mirror * (1.0 - shade)) + env;
}
