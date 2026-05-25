#version 330
const vec2 QUAD[6] = vec2[6](vec2(0,0), vec2(1,0), vec2(1,1), vec2(0,0), vec2(1,1), vec2(0,1));
uniform vec4 u_rect;
uniform vec2 u_resolution;
uniform vec3 u_color;
out vec2 v_uv;
void main() {
    vec2 vert = QUAD[gl_VertexID];
    v_uv = vert;
    vec2 pos_px = u_rect.xy + vert * u_rect.zw;
    vec2 ndc = (pos_px / u_resolution) * 2.0 - 1.0;
    ndc.y = -ndc.y;
    gl_Position = vec4(ndc, 0.0, 1.0);
}
