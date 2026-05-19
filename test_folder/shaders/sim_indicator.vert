#version 330
uniform mat4 u_vp;
in vec3 in_vert;
in vec3 in_color;
out vec3 v_color;
void main() {
    gl_Position = u_vp * vec4(in_vert, 1.0);
    v_color = in_color;
}
