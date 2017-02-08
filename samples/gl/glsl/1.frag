#version 420
precision mediump float;

uniform float time;
uniform vec2 screen;

out vec4 fragColor;

vec4 dither_rgba(float k, vec4 color);
vec4 hsv_to_rgb(float h, float s, float v, float a);

#define tau 6.28318530718

void main()
{
    vec2 pt = vec2(cos(time) * 0.25 + 0.5, sin(time) * 0.25 + 0.5);

    vec2 xy = gl_FragCoord.xy / screen.xy;
    float k = 255.0;
    float a = xy.x * 0.1 + 0.01;
    vec4 color = hsv_to_rgb(xy.y*2,
        1.0 - smoothstep(-2.0, +2.0, 
            sin(xy.x * cos(time/15.0) * 20.0) + cos(xy.y * sin(time / 15.0) * 20)),
        a, 1.0);
    fragColor = mix(
        dither_rgba(k, color),
        color,
        step(0.5, xy.y));
}

// https://github.com/hughsk/glsl-dither
float dither2x2(vec2 position) {
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

float dither_channel(float k, float a) {
    float lowband  = floor(a*k)/k;
    float brightness = fract(a*k);
    float limit = dither2x2(gl_FragCoord.xy);
    return lowband + step(limit, brightness)/k;
}

vec4 dither_rgba(float k, vec4 color) {
    return vec4(
        dither_channel(k, color.r),
        dither_channel(k, color.g),
        dither_channel(k, color.b),
        color.a);
}

// https://gist.github.com/eieio/4109795
vec4 hsv_to_rgb(float h, float s, float v, float a)
{
	float c = v * s;
	h = mod((h * 6.0), 6.0);
	float x = c * (1.0 - abs(mod(h, 2.0) - 1.0));
	vec4 color;

	if (0.0 <= h && h < 1.0) {
		color = vec4(c, x, 0.0, a);
	} else if (1.0 <= h && h < 2.0) {
		color = vec4(x, c, 0.0, a);
	} else if (2.0 <= h && h < 3.0) {
		color = vec4(0.0, c, x, a);
	} else if (3.0 <= h && h < 4.0) {
		color = vec4(0.0, x, c, a);
	} else if (4.0 <= h && h < 5.0) {
		color = vec4(x, 0.0, c, a);
	} else if (5.0 <= h && h < 6.0) {
		color = vec4(c, 0.0, x, a);
	} else {
		color = vec4(0.0, 0.0, 0.0, a);
	}

	color.rgb += v - c;

	return color;
}
