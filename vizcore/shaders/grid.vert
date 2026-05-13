#version 330

in vec2 in_pos;

uniform mat4 u_view_mat;
uniform mat4 u_proj_mat;
uniform vec3 u_camera_pos;

out vec2 v_coords;
out vec3 v_camera_pos;

void main() {
    const float grid_size = 100.0;

    vec3 world_pos = vec3(
        in_pos.x * grid_size,
        0.0,
        in_pos.y * grid_size
    );

    v_coords = world_pos.xz;
    v_camera_pos = u_camera_pos;

    gl_Position = u_proj_mat * u_view_mat * vec4(world_pos, 1.0);
}
