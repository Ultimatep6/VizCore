#version 330
uniform mat4 gVp;
uniform vec3 gRoomCenter;

in vec3 in_position;

out vec3 WorldPos;

void main() {
    WorldPos = in_position + gRoomCenter;
    gl_Position = gVp * vec4(WorldPos, 1.0);
}