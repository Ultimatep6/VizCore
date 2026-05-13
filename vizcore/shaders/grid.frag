#version 330

in vec2 v_coords;
in vec3 v_camera_pos;

out vec4 f_color;

vec2 mod_glsl(vec2 x, float y) {
    return x - y * floor(x / y);
}

void main() {
    const float grid_size = 100.0;
    const float cell_size = 1.0;
    const float subcell_size = 0.1;

    const float half_cell_size = cell_size * 0.5;
    const float half_subcell_size = subcell_size * 0.5;

    const vec4 cell_color = vec4(0.75, 0.75, 0.75, 0.55);
    const vec4 subcell_color = vec4(0.50, 0.50, 0.50, 0.45);

    const float cell_line_thickness = 0.01;
    const float subcell_line_thickness = 0.001;

    vec2 cell_coords = mod_glsl(v_coords + half_cell_size, cell_size);
    vec2 subcell_coords = mod_glsl(v_coords + half_subcell_size, subcell_size);

    vec2 distance_to_cell = abs(cell_coords - half_cell_size);
    vec2 distance_to_subcell = abs(subcell_coords - half_subcell_size);

    vec2 d = fwidth(v_coords);
    vec2 adjusted_cell_line_thickness = 0.5 * (vec2(cell_line_thickness) + d);
    vec2 adjusted_subcell_line_thickness = 0.5 * (vec2(subcell_line_thickness) + d);

    vec4 color = vec4(0.0);

    if (any(lessThan(distance_to_subcell, adjusted_subcell_line_thickness))) {
        color = subcell_color;
    }

    if (any(lessThan(distance_to_cell, adjusted_cell_line_thickness))) {
        color = cell_color;
    }

    const float height_to_fade_distance_ratio = 25.0;
    const float min_fade_distance = grid_size * 0.05;
    const float max_fade_distance = grid_size * 0.5;

    float fade_distance = abs(v_camera_pos.y) * height_to_fade_distance_ratio;
    fade_distance = clamp(fade_distance, min_fade_distance, max_fade_distance);

    float distance_to_camera = length(v_coords - v_camera_pos.xz);
    float opacity_falloff = smoothstep(1.0, 0.0, distance_to_camera / fade_distance);

    color.a *= opacity_falloff;

    if (color.a <= 0.001) {
        discard;
    }

    f_color = color;
}
