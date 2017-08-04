#version 450
#extension GL_ARB_separate_shader_objects : enable
#extension GL_ARB_shading_language_420pack : enable

layout (location = 0) in vec3 position;
layout (location = 1) in vec3 color;

layout (location = 0) out vec3 out_color;

layout (binding = 0) uniform SceneUBO {
    mat4 view;
} scene;

void main(void)
{
    out_color = color;
    gl_Position = scene.view * vec4(position, 1.0);
}
