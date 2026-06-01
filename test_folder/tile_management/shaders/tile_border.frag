#version 330

in vec2  v_uv;
in vec4  v_color;

out vec4 FragColor;

uniform float u_border_width = 0.04;
uniform float u_glow_falloff = 35.0;

void main() {
    // Distance to the nearest edge in local UV space.
    // min(v_uv, 1.0 - v_uv) gives 0.0 at each edge and 0.5 at the center.
    vec2  d         = min(v_uv, 1.0 - v_uv);
    float edge_dist = min(d.x, d.y);

    // Sharp neon border line
    float border = 1.0 - smoothstep(0.0, u_border_width, edge_dist);

    // Soft exponential glow bleeding outward from the border
    float glow = exp(-edge_dist * u_glow_falloff);

    // Bright white/blue core sits on top of the tinted glow
    vec3 core_color = mix(v_color.rgb, vec3(0.85, 0.96, 1.0), border * 0.6);
    vec3 color      = v_color.rgb * glow * 1.6 + core_color * border;

    float alpha = max(border, glow * 0.72);

    FragColor = vec4(color, alpha);
}
