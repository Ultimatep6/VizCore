#version 330
in vec2 in_vert;
uniform mat4 mvp;

void main() {
    gl_Position = mvp * vec4(in_vert, 0.0, 1.0);
}