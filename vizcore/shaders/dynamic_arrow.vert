#version 330

in vec3 in_vert;
in vec3 in_color;
in mat3 in_rotation;  // per-vertex rotation matrix for dynamic signals
in float in_scale;     // per-vertex scaling for dynamic signals

uniform mat4 mvp;

out vec3 v_color;

void main() {
    // Apply per-vertex rotation and scaling
    vec3 scaled = vec3(in_vert.x, in_vert.y, in_vert.z * in_scale);
    vec3 rotated = in_rotation * scaled;
    gl_Position = mvp * vec4(rotated, 1.0);
    v_color = in_color;
}