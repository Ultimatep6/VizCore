#version 330
uniform mat4 u_vp;
uniform float u_radius;
uniform vec3 u_color;
in vec3 in_vert;
in vec3 in_normal;
in vec3 in_pos;
out vec3 v_normal;
out vec3 v_color;
void main() {
    vec3 world_pos = in_vert * u_radius + in_pos;
    gl_Position = u_vp * vec4(world_pos, 1.0);
    v_normal = in_normal;
    v_color = u_color;
}
