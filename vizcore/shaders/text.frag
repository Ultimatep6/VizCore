#version 330

in vec2 v_uv;

uniform sampler2D u_atlas;
uniform vec4 u_color;

out vec4 f_color;

void main() {
    float alpha = texture(u_atlas, v_uv).r;
    f_color = vec4(u_color.rgb, u_color.a * alpha);
}