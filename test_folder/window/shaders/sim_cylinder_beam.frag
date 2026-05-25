#version 330 core

in vec3 v_color;
in float v_height;
out vec4 f_color;

void main() {
    f_color = vec4(v_color, 0.5);
}
