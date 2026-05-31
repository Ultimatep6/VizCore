#version 330
#define MAX_INSTANCES 64
#define BLIP_RADIUS 0.5
uniform mat4 u_vp;
uniform vec4 u_translations[MAX_INSTANCES];
uniform vec3 u_camera_pos;
out vec3 v_center;
out vec3 v_world_pos;
void main() {
    vec3 center = u_translations[gl_InstanceID].xyz;
    int tri = gl_VertexID / 3;
    int vid = gl_VertexID % 3;
    const int idx[36] = int[36](
        0,1,2, 0,2,3,
        4,5,6, 4,6,7,
        0,1,5, 0,5,4,
        2,3,7, 2,7,6,
        0,3,7, 0,7,4,
        1,2,6, 1,6,5
    );
    int c = idx[gl_VertexID];
    float x = float((c & 1) == 1) * 2.0 - 1.0;
    float y = float((c & 2) == 2) * 2.0 - 1.0;
    float z = float((c & 4) == 4) * 2.0 - 1.0;
    vec3 pos = center + vec3(x, y, z) * BLIP_RADIUS;
    v_center = center;
    v_world_pos = pos;
    gl_Position = u_vp * vec4(pos, 1.0);
}
