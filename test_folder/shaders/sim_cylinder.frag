#version 330 core

out vec4 FragColor;

uniform vec2 u_resolution;
uniform vec3 u_cam_pos;
uniform mat4 u_inv_view;
uniform mat4 u_model[2]; // [0] = model, [1] = inv_model
uniform vec4 u_cylinder; // (base_y, top_y, radius, _)
uniform vec3 u_color;
uniform float u_fov;     // vertical FOV in radians

vec3 transformPoint(mat4 m, vec3 p) {
    return (m * vec4(p, 1.0)).xyz;
}

vec3 transformDir(mat4 m, vec3 d) {
    return (m * vec4(d, 0.0)).xyz;
}

void main() {
    float aspect = u_resolution.x / u_resolution.y;
    float tanHalfFov = tan(u_fov * 0.5);

    vec2 screen = (gl_FragCoord.xy / u_resolution) * 2.0 - 1.0;

    vec3 rdView = normalize(vec3(
        screen.x * tanHalfFov * aspect,
        screen.y * tanHalfFov,
        -1.0
    ));

    vec3 ro = u_cam_pos;
    vec3 rd = normalize(transformDir(u_inv_view, rdView));

    vec3 roLocal = transformPoint(u_model[1], ro);
    vec3 rdLocal = normalize(transformDir(u_model[1], rd));

    float baseY = u_cylinder.x;
    float topY  = u_cylinder.y;
    float R     = u_cylinder.z;

    // Ray-cylinder intersection (infinite cylinder along Y axis)
    float a = rdLocal.x * rdLocal.x + rdLocal.z * rdLocal.z;
    float b = 2.0 * (roLocal.x * rdLocal.x + roLocal.z * rdLocal.z);
    float c = roLocal.x * roLocal.x + roLocal.z * roLocal.z - R * R;
    float disc = b * b - 4.0 * a * c;

    float alpha = 0.0;

    if (disc >= 0.0 && a > 1e-8) {
        float sqrtDisc = sqrt(disc);
        float t1 = (-b - sqrtDisc) / (2.0 * a);
        float t2 = (-b + sqrtDisc) / (2.0 * a);

        vec3 p1 = roLocal + t1 * rdLocal;
        vec3 p2 = roLocal + t2 * rdLocal;

        bool hit = false;
        if (t1 > 0.0 && p1.y >= baseY && p1.y <= topY) hit = true;
        if (t2 > 0.0 && p2.y >= baseY && p2.y <= topY) hit = true;

        if (hit) {
            alpha = 0.6;
        }
    }

    // Anti-aliased edge: if no hard hit, check closest approach
    if (alpha < 0.01) {
        float tClosest = -(roLocal.x * rdLocal.x + roLocal.z * rdLocal.z) / (a + 1e-8);
        if (tClosest > 0.0) {
            vec3 closest = roLocal + tClosest * rdLocal;
            float clampedY = clamp(closest.y, baseY, topY);
            float distToAxis = length(vec2(closest.x, closest.z));

            // Soft edge width in world units, scaled by distance
            float worldEdge = R * 0.5 + 0.01 * tClosest;
            float edgeAlpha = 1.0 - smoothstep(0.0, worldEdge, distToAxis - R);

            // Fade out near the ends
            float endFade = 1.0;
            float endWidth = 0.1;
            if (closest.y < baseY + endWidth)
                endFade = smoothstep(baseY, baseY + endWidth, closest.y);
            if (closest.y > topY - endWidth)
                endFade = min(endFade, smoothstep(topY, topY - endWidth, closest.y));

            alpha = edgeAlpha * endFade * 0.6;
        }
    }

    if (alpha > 0.01) {
        FragColor = vec4(u_color, alpha);
    } else {
        FragColor = vec4(0.0);
    }
}
