#version 330

in vec3 in_position;

uniform mat4 mvp;
uniform vec3 gRoomCenter;
uniform float gRoomSize;

out vec3 WorldPos;

void main() {
    vec3 worldPos = in_position + gRoomCenter;
    gl_Position = mvp * vec4(worldPos, 1.0);
    WorldPos = worldPos;
}