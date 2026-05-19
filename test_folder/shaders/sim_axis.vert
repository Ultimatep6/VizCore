#version 330
uniform mat4 u_vp;
uniform vec3 u_offset;
uniform float u_scale;
uniform mat3 u_rotation;
uniform vec3 u_color_override;
uniform int u_use_override;

in vec3 in_vert;
in vec3 in_color;

out vec3 v_color;

void main() {
    vec3 rotated = u_rotation * in_vert;
    gl_Position = u_vp * vec4((rotated * u_scale) + u_offset, 1.0);
    v_color = u_use_override > 0 ? u_color_override : in_color;
}