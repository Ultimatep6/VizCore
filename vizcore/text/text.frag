#version 330
uniform sampler2D u_atlas;  // Font atlas texture
uniform vec4 u_color;       // Text color (r, g, b, a)
in vec2 v_uv;
out vec4 f_color;

void main() {
    float alpha = texture(u_atlas, v_uv).r;  // Sample grayscale atlas
    f_color = vec4(u_color.rgb, u_color.a * alpha);
}