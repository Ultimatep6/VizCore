#version 330 core

uniform mat4 mvp;
uniform float R;
uniform vec3 u_color; 

out vec2 u_uv;
out vec3 rgbColor;    

const vec2 i_verts[4] = vec2[4](
    vec2(1.0, 1.0),
    vec2(1.0, -1.0),
    vec2(-1.0, 1.0),
    vec2(-1.0, -1.0)
);

void main() {
    int index = gl_VertexID;
    if (index >= 4) index = 0; 

    vec2 pos = i_verts[index];
    
    gl_Position = mvp * vec4(R * pos.x, 0.0, R * pos.y, 1.0);
    u_uv = pos;
    
    rgbColor = u_color; 
}
