#version 330

#define RGB_BORDER vec3(0.05, 0.45, 1.0)
#define BORDER_THICKNESS = 0.04
#define GLOW_FALLOFF = 35.0
#define ALPHA_THRESH = 0.01

in vec2  v_uv;

out vec4 FragColor;

void main() {
    vec2  d         = min(v_uv, 1.0 - v_uv);
    float edge_dist = min(d.x, d.y);

    float border = 1.0 - smoothstep(0.0, BORDER_THICKNESS, edge_dist);
    float glow   = exp(-edge_dist * GLOW_FALLOFF);

    vec3 core_color = mix(RGB_BORDER, vec3(0.45, 0.8, 1.0), border * 0.6);
    vec3 color      = RGB_BORDER * glow * 1.6 + core_color * border;
    float alpha     = max(border, glow * 0.72);

    if (alpha < ALPHA_THRESH) discard;
    FragColor = vec4(color, alpha);
}
