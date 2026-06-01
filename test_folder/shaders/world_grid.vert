#version 330
uniform mat4 gVp;
uniform vec3 gRoomCenter;
uniform float gRoomSize;
in vec3 in_position;

out vec3 WorldPos;

void main() {
    vec3 worldPos = in_position + gRoomCenter;
    gl_Position = gVp * vec4(worldPos, 1.0);
    WorldPos = worldPos;
}
