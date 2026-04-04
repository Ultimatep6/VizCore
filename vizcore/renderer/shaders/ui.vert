#version 330
in vec2 in_vert;
uniform vec2 u_pos;
uniform vec2 u_size;
uniform vec2 u_resolution;
void main() {
    vec2 pos = in_vert * u_size + u_pos;
    gl_Position = vec4((pos / u_resolution) * 2.0 - 1.0, 0.0, 1.0);
}
