#version 330

const vec2 QUAD[6] = vec2[6](
    vec2(0.0, 0.0),
    vec2(1.0, 0.0),
    vec2(1.0, 1.0),
    vec2(0.0, 0.0),
    vec2(1.0, 1.0),
    vec2(0.0, 1.0)
);

uniform vec4 inst_rect;
out vec2 v_uv;

uniform vec2 u_resolution;

void main() {
    vec2 vert    = QUAD[gl_VertexID];
    v_uv         = vert;

    vec2 pos_px  = inst_rect.xy + vert * inst_rect.zw;
    vec2 ndc     = (pos_px / u_resolution) * 2.0 - 1.0;
    gl_Position  = vec4(ndc, 0.0, 1.0);
}
