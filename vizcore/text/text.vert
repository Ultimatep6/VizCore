#version 330
in vec2 in_vert;
in vec2 in_uv;
uniform mat4 u_projection;
out vec2 v_uv;

void main() {
    gl_Position = u_projection * vec4(in_vert, 0.0, 1.0);
    v_uv = in_uv;
}