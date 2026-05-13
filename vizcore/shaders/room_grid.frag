#version 330

in vec3 WorldPos;
out vec4 FragColor;

uniform vec3 gRoomCenter;
uniform float gRoomSize;
uniform float gGridMinPixelsBetweenCells = 2.0;
uniform float gGridCellSize = 0.1025;
uniform vec4 gGridColorFloor = vec4(0.5, 0.5, 0.5, 1.0);
uniform vec4 gGridColorWall = vec4(0.7, 0.7, 0.7, 1.0);

float log10(float x) {
    return log(x) / log(10.0);
}

float satf(float x) {
    return clamp(x, 0.0, 1.0);
}

vec2 satv2(vec2 x) {
    return clamp(x, 0.0, 1.0);
}

vec4 get_grid_color(vec2 coords, vec2 dudv) {
    float l = length(dudv);
    float LOD = max(0.0, log10(l * gGridMinPixelsBetweenCells / gGridCellSize) + 1.0);

    float cellSizeLod0 = gGridCellSize * pow(10.0, floor(LOD));
    float cellSizeLod1 = cellSizeLod0 * 10.0;
    float cellSizeLod2 = cellSizeLod1 * 10.0;

    dudv *= 4.0;

    vec2 temp = mod(coords, cellSizeLod0) / dudv;
    vec2 temp2 = vec2(1.0) - abs(satv2(temp) * 2.0 - vec2(1.0));
    float lod0a = max(temp2.x, temp2.y);

    temp = mod(coords, cellSizeLod1) / dudv;
    temp2 = vec2(1.0) - abs(satv2(temp) * 2.0 - vec2(1.0));
    float lod1a = max(temp2.x, temp2.y);

    temp = mod(coords, cellSizeLod2) / dudv;
    temp2 = vec2(1.0) - abs(satv2(temp) * 2.0 - vec2(1.0));
    float lod2a = max(temp2.x, temp2.y);

    float lodFade = fract(LOD);
    vec4 color;

    if (lod2a > 0.0) {
        color = gGridColorWall;
        color.a *= lod2a;
    } else if (lod1a > 0.0) {
        color = mix(gGridColorWall, gGridColorFloor, lodFade);
        color.a *= lod1a;
    } else {
        color = gGridColorFloor;
        color.a *= (lod0a * (1.0 - lodFade));
    }

    return color;
}

void main() {
    float halfSize = gRoomSize * 0.5;
    float epsilon = 0.1;

    vec4 color = vec4(0.0);

    // Floor (Y = center_y)
    if (abs(WorldPos.y - gRoomCenter.y) < epsilon) {
        vec2 dvx = vec2(dFdx(WorldPos.x), dFdy(WorldPos.x));
        vec2 dvy = vec2(dFdx(WorldPos.z), dFdy(WorldPos.z));
        vec2 dudv = vec2(length(dvx), length(dvy));
        dudv = max(dudv, vec2(0.001));
        color = get_grid_color(WorldPos.xz, dudv);
    }

    // Wall +X (X = center_x + halfSize)
    else if (abs(WorldPos.x - (gRoomCenter.x + halfSize)) < epsilon) {
        vec2 dvx = vec2(dFdx(WorldPos.y), dFdy(WorldPos.y));
        vec2 dvy = vec2(dFdx(WorldPos.z), dFdy(WorldPos.z));
        vec2 dudv = vec2(length(dvx), length(dvy));
        dudv = max(dudv, vec2(0.001));
        color = get_grid_color(WorldPos.yz, dudv);
    }

    // Wall -X (X = center_x - halfSize)
    else if (abs(WorldPos.x - (gRoomCenter.x - halfSize)) < epsilon) {
        vec2 dvx = vec2(dFdx(WorldPos.y), dFdy(WorldPos.y));
        vec2 dvy = vec2(dFdx(WorldPos.z), dFdy(WorldPos.z));
        vec2 dudv = vec2(length(dvx), length(dvy));
        dudv = max(dudv, vec2(0.001));
        color = get_grid_color(WorldPos.yz, dudv);
    }

    // Wall +Z (Z = center_z + halfSize)
    else if (abs(WorldPos.z - (gRoomCenter.z + halfSize)) < epsilon) {
        vec2 dvx = vec2(dFdx(WorldPos.x), dFdy(WorldPos.x));
        vec2 dvy = vec2(dFdx(WorldPos.y), dFdy(WorldPos.y));
        vec2 dudv = vec2(length(dvx), length(dvy));
        dudv = max(dudv, vec2(0.001));
        color = get_grid_color(WorldPos.xy, dudv);
    }

    // Wall -Z (Z = center_z - halfSize)
    else if (abs(WorldPos.z - (gRoomCenter.z - halfSize)) < epsilon) {
        vec2 dvx = vec2(dFdx(WorldPos.x), dFdy(WorldPos.x));
        vec2 dvy = vec2(dFdx(WorldPos.y), dFdy(WorldPos.y));
        vec2 dudv = vec2(length(dvx), length(dvy));
        dudv = max(dudv, vec2(0.001));
        color = get_grid_color(WorldPos.xy, dudv);
    }

    FragColor = color;
}