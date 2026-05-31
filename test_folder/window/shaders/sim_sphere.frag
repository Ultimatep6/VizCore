#version 330
in vec3 v_normal;
in vec3 v_color;
out vec4 FragColor;
void main() {
    vec3 lightDir = normalize(vec3(0.5, 1.0, 0.3));
    float diff = max(dot(normalize(v_normal), lightDir), 0.0);
    vec3 lit = v_color * (0.4 + 0.6 * diff);
    FragColor = vec4(lit, 1.0);
}
