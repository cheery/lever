shaders: glsl/*.spv

%_frag.spv: %.frag
	glslangValidator $< -V -o $@

%_vert.spv: %.vert
	glslangValidator $< -V -o $@
