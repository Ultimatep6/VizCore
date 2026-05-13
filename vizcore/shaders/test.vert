#version 330

in vec3 in_position;
in vec3 in_color;

uniform mat4 u_model_mat;
uniform mat4 u_view_mat;
uniform mat4 u_proj_mat;

out vec3 v_color;

void main() {
    v_color = in_color;
    gl_Position = u_proj_mat * u_view_mat * u_model_mat * vec4(in_position, 1.0);
}