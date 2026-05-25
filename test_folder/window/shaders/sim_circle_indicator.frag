#version 330 core

in vec2 u_uv;
in vec3 rgbColor;
out vec4 f_color;

float circle(vec2 uv, float radius) {
    float d = dot(uv, uv);
    return 1.0 - smoothstep(radius - radius * 0.01, radius + radius * 0.01, d);
}

void main() {
    float alpha = circle(u_uv, 1.0);
    if (alpha < 0.01) discard;
    
    f_color = vec4(rgbColor, alpha);
}
