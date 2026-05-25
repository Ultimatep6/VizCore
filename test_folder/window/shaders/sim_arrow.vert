#version 330 core

#define SEGMENTS     32
#define SHAFT_RADIUS 0.04
#define SHAFT_HEIGHT 0.6
#define HEAD_RADIUS  0.10
#define HEAD_HEIGHT  0.2
#define MAX_INSTANCES

uniform mat4 u_vp;
uniform mat4 u_models[MAX_INSTANCES];
uniform vec3 u_colors[MAX_INSTANCES];

out vec3 v_color;

const float PI = 3.14159265359;

void main() {
    int   N      = SEGMENTS;
    int   vid    = gl_VertexID;
    int   inst   = gl_InstanceID;
    float base_y = SHAFT_HEIGHT;
    float tip_y  = SHAFT_HEIGHT + HEAD_HEIGHT;

    vec3 pos;

    if (vid < 6 * N) {
        int   seg   = vid / 6;
        int   local = vid % 6;
        float a0    = float(seg)     * 2.0 * PI / float(N);
        float a1    = float(seg + 1) * 2.0 * PI / float(N);
        float c0 = cos(a0), s0 = sin(a0);
        float c1 = cos(a1), s1 = sin(a1);

        if      (local == 0) pos = vec3(c0 * SHAFT_RADIUS, 0.0,          s0 * SHAFT_RADIUS);
        else if (local == 1) pos = vec3(c0 * SHAFT_RADIUS, SHAFT_HEIGHT, s0 * SHAFT_RADIUS);
        else if (local == 2) pos = vec3(c1 * SHAFT_RADIUS, SHAFT_HEIGHT, s1 * SHAFT_RADIUS);
        else if (local == 3) pos = vec3(c0 * SHAFT_RADIUS, 0.0,          s0 * SHAFT_RADIUS);
        else if (local == 4) pos = vec3(c1 * SHAFT_RADIUS, SHAFT_HEIGHT, s1 * SHAFT_RADIUS);
        else                 pos = vec3(c1 * SHAFT_RADIUS, 0.0,          s1 * SHAFT_RADIUS);

    } else if (vid < 9 * N) {
        int   seg   = (vid - 6 * N) / 3;
        int   local = (vid - 6 * N) % 3;
        float a0    = float(seg)     * 2.0 * PI / float(N);
        float a1    = float(seg + 1) * 2.0 * PI / float(N);

        if      (local == 0) pos = vec3(0.0,                  0.0, 0.0);
        else if (local == 1) pos = vec3(cos(a1) * SHAFT_RADIUS, 0.0, sin(a1) * SHAFT_RADIUS);
        else                 pos = vec3(cos(a0) * SHAFT_RADIUS, 0.0, sin(a0) * SHAFT_RADIUS);

    } else if (vid < 12 * N) {
        int   seg   = (vid - 9 * N) / 3;
        int   local = (vid - 9 * N) % 3;
        float a0    = float(seg)     * 2.0 * PI / float(N);
        float a1    = float(seg + 1) * 2.0 * PI / float(N);

        if      (local == 0) pos = vec3(cos(a0) * HEAD_RADIUS, base_y, sin(a0) * HEAD_RADIUS);
        else if (local == 1) pos = vec3(cos(a1) * HEAD_RADIUS, base_y, sin(a1) * HEAD_RADIUS);
        else                 pos = vec3(0.0,                   tip_y,  0.0);

    } else {
        int   seg   = (vid - 12 * N) / 3;
        int   local = (vid - 12 * N) % 3;
        float a0    = float(seg)     * 2.0 * PI / float(N);
        float a1    = float(seg + 1) * 2.0 * PI / float(N);

        if      (local == 0) pos = vec3(0.0,                  base_y, 0.0);
        else if (local == 1) pos = vec3(cos(a1) * HEAD_RADIUS, base_y, sin(a1) * HEAD_RADIUS);
        else                 pos = vec3(cos(a0) * HEAD_RADIUS, base_y, sin(a0) * HEAD_RADIUS);
    }

    gl_Position = u_vp * u_models[inst] * vec4(pos, 1.0);
    v_color = u_colors[inst];
}
