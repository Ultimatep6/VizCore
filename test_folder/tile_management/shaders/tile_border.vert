#version 330

const vec2 QUAD[6] = vec2[6](
    vec2(0.0, 0.0),
    vec2(1.0, 0.0),
    vec2(1.0, 1.0),
    vec2(0.0, 0.0),
    vec2(1.0, 1.0),
    vec2(0.0, 1.0)
);

in vec4 inst_rect;   // x, y, w, h  in NDC
in vec4 inst_color;  // r, g, b, a  neon tint

out vec2 v_uv;
out vec4 v_color;

void main() {
    vec2 vert     = QUAD[gl_VertexID];
    v_uv          = vert;
    v_color       = inst_color;
    vec2 world_pos = inst_rect.xy + vert * inst_rect.zw;
    gl_Position   = vec4(world_pos, 0.0, 1.0);
}
