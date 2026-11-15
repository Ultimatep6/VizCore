#version 330
#define BLIP_RADIUS 0.5
#define BLIP_COLOR vec3(0.3, 0.8, 0.9)
uniform vec3 u_camera_pos;
in vec3 v_center;
in vec3 v_world_pos;
out vec4 FragColor;
void main() {
    vec3 ray_dir = normalize(v_world_pos - u_camera_pos);
    vec3 oc = u_camera_pos - v_center;
    float a = dot(ray_dir, ray_dir);
    float b = 2.0 * dot(oc, ray_dir);
    float c = dot(oc, oc) - BLIP_RADIUS * BLIP_RADIUS;
    float disc = b * b - 4.0 * a * c;
    if (disc < 0.0)
        discard;
    float t = (-b - sqrt(disc)) / (2.0 * a);
    vec3 hit = u_camera_pos + t * ray_dir;
    vec3 n = normalize(hit - v_center);
    vec3 light = normalize(vec3(0.5, 1.0, 0.3));
    float diff = max(dot(n, light), 0.0);
    FragColor = vec4(BLIP_COLOR * (0.4 + 0.6 * diff), 1.0);
}
