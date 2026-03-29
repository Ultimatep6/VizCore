import struct
import moderngl

# generally speaking you always want 2^n bits 

ctx = moderngl.create_context(standalone=True)

points = [
    0.0, 1.0,
    -0.5, 0.0,
    0.5, 0.0
]

vert_buffer = struct.pack("6f", *points)        # array of 6 floats with 4 bytes = 24 bytes

vbo = ctx.buffer(vert_buffer)

vao = ctx.vertex_array(
    shader_program,
    [
        (vbo, "2f", "in_vert"), # <---- Each vertex is composed by 2 consecutive values in the array
    ],
    index_buffer_object

)

# or

vao = ctx.vertex_array(
    shader_program,
    [
        (vbo, "2f 3u x", "in_vert", "in_color"), # <---- Each vertex is composed by x,y r,g,b margin
    ],
    index_buffer_object

)

# inefficient, each vertex contains the color but why not just make it per instance. Rather than color each cubes face individually, color each cube directly

#or 

vao = ctx.vertex_array(
    shader_program,
    [
        (vbo_verts_normals, "3f 3f /v", "in_vert", "in_normals"), # <---- Each vertex is composed by x,y r,g,b margin
        (vbo_colors, "3u /i", "in_color"),  # <---- Autmatically normalizes the entry to 0,1
    ],
    index_buffer_object
)

# Now we get the vertex coordinates, the normal vectors of each face of a cube. Each cube gets a color
# --------------------------------------------------------------------------------------------------


prog = ctx.program(
    vertex_shader=None,
    fragment_shader=None,
)
vao = ctx.simple_vertex_array(prog, vbo, 'in_vert', 'in_color')

# is short for 

vao = ctx.vertex_array(
    shader_program,
    [(vbo, "2f 3f1", "in_vert", "in_color")],  # <- Format string describes layout
    index_buffer_object
)