#version 330
in float in_y_val; // The raw data point
in float in_index; // The index [0...N]

uniform float u_min;
uniform float u_max;
uniform float u_plot_x;
uniform float u_plot_y;
uniform float u_plot_width;
uniform float u_plot_height;
uniform vec2 u_resolution; // (W, H)
uniform float u_points_per_channel; // Dynamic number of points in the buffer

void main() {
    float x_norm = in_index / (u_points_per_channel - 1.0);
    float y_norm = (in_y_val - u_min) / (u_max - u_min);

    // Compute pixel coords within the actual plot rectangle
    float x_px = u_plot_x + x_norm * u_plot_width;
    float y_px = u_plot_y + y_norm * u_plot_height;

    // Final NDC mapping using the full window resolution
    gl_Position = vec4((x_px / u_resolution.x) * 2.0 - 1.0, 
                       (y_px / u_resolution.y) * 2.0 - 1.0, 0.0, 1.0);
}
