#version 330
in vec2 v_pos;
out vec4 f_color;

uniform vec4 u_color;
uniform vec4 u_border_color;
uniform vec2 u_size;
uniform float u_radius;
uniform float u_border_width;

float rounded_box_sdf(vec2 pos, vec2 size, float radius) {
    vec2 d = abs(pos - size * 0.5) - (size * 0.5 - radius);
    return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0) - radius;
}

void main() {
    vec2 pixel_pos = v_pos * u_size;
    float dist = rounded_box_sdf(pixel_pos, u_size, u_radius);
    
    if (dist > 1.0) {
        discard;
    }
    
    // Smooth boundary
    float border = smoothstep(1.0, -1.0, dist);
    float interior = smoothstep(u_border_width + 0.5, u_border_width - 0.5, -dist);
    
    f_color = mix(u_border_color, u_color, interior);
    f_color.a *= border;
}