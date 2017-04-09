# This rule depends on the fact that the .spv files
# are already compiled once. It's a bit flawed that way.
shaders: glsl/*.spv

%.spv: %.frag
	glslangValidator $< -V -o $@

%.spv: %.vert
	glslangValidator $< -V -o $@
