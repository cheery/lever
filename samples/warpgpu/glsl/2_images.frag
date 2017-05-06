#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec2 position;

layout (location = 0) out vec4 frag_color;

layout (binding = 1) uniform sampler2D texSampler;

layout (push_constant) uniform Push {
    float time;
} g;

float voronoi( in vec2 x, in float time );

void main(void)
{
    vec2 tu = (position.xy - 1.0) / 2.0;
    tu = vec2(tu.x + voronoi(tu * 20.0, g.time) * 0.05, tu.y);
    frag_color = texture(texSampler, tu);
}

vec2 hash( vec2 p ){
	p = vec2( dot(p,vec2(127.1,311.7)),dot(p,vec2(269.5,183.3)));
	return fract(sin(p)*43758.5453);
}

/* This voronoi implementation was available at
    https://gist.github.com/patriciogonzalezvivo/670c22f3966e662d2f83
    More can be found by searching 'glsl voronoi' */
#define SWITCH_TIME 	60.0		// seconds

float voronoi( in vec2 x, in float time ){
    float t = time/SWITCH_TIME;
    float function 			= mod(t,4.0);
    bool  multiply_by_F1	= mod(t,8.0)  >= 4.0;
    bool  inverse				= mod(t,16.0) >= 8.0;
    float distance_type	= mod(t/16.0,4.0);

	vec2 n = floor( x );
	vec2 f = fract( x );
	
	float F1 = 8.0;
	float F2 = 8.0;
	
	for( int j=-1; j<=1; j++ )
		for( int i=-1; i<=1; i++ ){
			vec2 g = vec2(i,j);
			vec2 o = hash( n + g );

			o = 0.5 + 0.41*sin( time + 6.2831*o );	
			vec2 r = g - f + o;

		float d = 	distance_type < 1.0 ? dot(r,r)  :				// euclidean^2
				  	distance_type < 2.0 ? sqrt(dot(r,r)) :			// euclidean
					distance_type < 3.0 ? abs(r.x) + abs(r.y) :		// manhattan
					distance_type < 4.0 ? max(abs(r.x), abs(r.y)) :	// chebyshev
					0.0;

		if( d<F1 ) { 
			F2 = F1; 
			F1 = d; 
		} else if( d<F2 ) {
			F2 = d;
		}
    }
	
	float c = function < 1.0 ? F1 : 
			  function < 2.0 ? F2 : 
			  function < 3.0 ? F2-F1 :
			  function < 4.0 ? (F1+F2)/2.0 : 
			  0.0;
		
	if( multiply_by_F1 )	c *= F1;
	if( inverse )			c = 1.0 - c;
	
    return c;
}
