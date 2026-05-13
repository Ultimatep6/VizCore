#version 330

in vec3 in_position;

uniform mat4 mvp;
uniform vec3 uOffset;
uniform float uScale;

void main() {
    vec3 worldPos = (in_position * uScale) + uOffset;
    gl_Position = mvp * vec4(worldPos, 1.0);
}