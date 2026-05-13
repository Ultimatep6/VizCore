#version 330

in vec3 in_vert;
in vec3 in_color;

uniform mat4 mvp;
uniform float uScale;

out vec3 v_color;

void main() {
    gl_Position = mvp * vec4(in_vert * uScale, 1.0);
    v_color = in_color;
}