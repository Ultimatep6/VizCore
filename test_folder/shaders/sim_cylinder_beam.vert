#version 330 core

#define SEGMENTS 24
#define PI 3.14159265359

uniform mat4 u_vp;
uniform mat4 u_models[16];
uniform vec3 u_colors[16];

out vec3 v_color;

void main() {
    int tri = gl_VertexID % 6;
    int seg = gl_VertexID / 6;
    int inst = gl_InstanceID;

    float a0 = 2.0 * PI * float(seg) / float(SEGMENTS);
    float a1 = 2.0 * PI * float(seg + 1) / float(SEGMENTS);

    float c0 = cos(a0), s0 = sin(a0);
    float c1 = cos(a1), s1 = sin(a1);

    vec3 pos;
    if (tri == 0)      pos = vec3(c0, 1.0, s0);
    else if (tri == 1) pos = vec3(c0, 0.0, s0);
    else if (tri == 2) pos = vec3(c1, 1.0, s1);
    else if (tri == 3) pos = vec3(c0, 0.0, s0);
    else if (tri == 4) pos = vec3(c1, 0.0, s1);
    else               pos = vec3(c1, 1.0, s1);

    gl_Position = u_vp * u_models[inst] * vec4(pos, 1.0);
    v_color = u_colors[inst];
}
