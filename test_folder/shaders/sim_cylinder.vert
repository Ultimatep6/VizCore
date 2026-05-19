#version 330 core

const vec2 quad_verts[4] = vec2[4](
    vec2( 1.0,  1.0),
    vec2( 1.0, -1.0),
    vec2(-1.0,  1.0),
    vec2(-1.0, -1.0)
);

void main() {
    gl_Position = vec4(quad_verts[gl_VertexID % 4], 0.0, 1.0);
}
