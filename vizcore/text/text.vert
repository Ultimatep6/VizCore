#version 330

in vec3 in_vert;
in vec2 in_uv;

uniform mat4 mvp;

out vec2 v_uv;

void main() {
    gl_Position = mvp * vec4(in_vert, 1.0);
    v_uv = in_uv;
}