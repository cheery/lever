#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

#define pi  3.14159265359
#define tau 6.28318530718

layout (location = 0) out vec4 frag_color;

layout (push_constant) uniform Push {
    float time;
} g;

vec3 ocean_wave(vec2 dir, float w, float speed, float a);
vec4 dither_rgba(float k, vec4 color);

void main(void)
{
    float L1 = 20.0;
    float L2 = 10.0;
    float L3 = 40.0;

    float L1_speed = tau * sqrt(9.8 * tau / L1 * 50);
    float L2_speed = tau * sqrt(9.8 * tau / L2 * 50);
    float L3_speed = tau * sqrt(9.8 * tau / L3 * 50);

    vec3 test = vec3(0.0);
    test += ocean_wave(
        normalize(vec2(1.0,+0.5)),
        2/L1, L1_speed, L1*0.05);
    test += ocean_wave(
        normalize(vec2(1.0,+0.3)),
        2/L2, L2_speed, L2*0.05*sin(g.time / 24.0));
    test += ocean_wave(
        normalize(vec2(1.0,-0.3)),
        2/L3, L3_speed, L3*0.05*sin(g.time / 20.0));
    test += ocean_wave(
        normalize(vec2(1.0, 0.0)),
        2/L2, L2_speed, L2*0.05);

    vec3 n = normalize(
        cross(
            vec3(1.0, test.y, 0.0),
            vec3(0.0, 1.0, test.z)));

    vec3 lightSource = normalize(vec3(0.5, 1.0, 0.0));

    float refl = dot(reflect(vec3(0, 1, 0), n), lightSource);

    frag_color = vec4(vec3( dot(n, lightSource) * 0.7 + 0.5)
                    * vec3(0.3, 0.5, 1.0) + 
                    smoothstep(0.8925, 0.915, refl)
                    * vec3(1.0, 0.5, 0.2), 1.0);
    frag_color = dither_rgba(255.0, frag_color);
}

vec3 ocean_wave(vec2 dir, float w, float speed, float a)
{
    float k = 2.0;

    float p = dot(dir, gl_FragCoord.xy * w) + g.time * speed * w;
    float s = sin(p)*0.5;
    float c = cos(p);

    return vec3(
        2.0*a * pow(s, k),
        k * w * dir.x * a * pow(s, k-1) * c,
        k * w * dir.y * a * pow(s, k-1) * c);
}

// https://github.com/hughsk/glsl-dither
float dither2x2(vec2 position)
{
  int x = int(mod(position.x, 2.0));
  int y = int(mod(position.y, 2.0));
  int index = x + y * 2;
  float limit = 0.0;

  if (x < 8) {
    if (index == 0) limit = 0.25;
    if (index == 1) limit = 0.75;
    if (index == 2) limit = 1.00;
    if (index == 3) limit = 0.50;
  }
  return limit;
}

float dither_channel(float k, float a)
{
    float lowband  = floor(a*k)/k;
    float brightness = fract(a*k);
    float limit = dither2x2(gl_FragCoord.xy);
    return lowband + step(limit, brightness)/k;
}

vec4 dither_rgba(float k, vec4 color)
{
    return vec4(
        dither_channel(k, color.r),
        dither_channel(k, color.g),
        dither_channel(k, color.b),
        color.a);
}
