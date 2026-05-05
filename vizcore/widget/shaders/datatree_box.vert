#version 330
in vec2 in_vert;
uniform mat4 mvp;
uniform vec2 u_size;

out vec2 v_pos;

void main() {
    v_pos = in_vert;
    vec2 scaled = in_vert * u_size;
    gl_Position = mvp * vec4(scaled, 0.0, 1.0);
}