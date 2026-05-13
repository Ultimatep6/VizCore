#version 330

in vec3 in_vert;
in vec3 in_color;

uniform mat4 mvp;

out vec3 v_color;

void main() {
    // Apply per-vertex rotation and scaling
    gl_Position = mvp * vec4(in_vert, 1.0);
    v_color = in_color;
}