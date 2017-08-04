SOURCES = $(wildcard glsl/*.frag glsl/*.vert)

SPV = $(patsubst %, %.spv, $(SOURCES))

shaders: $(SPV)

%.frag.spv: %.frag
	glslangValidator $< -V -o $@

%.vert.spv: %.vert
	glslangValidator $< -V -o $@
