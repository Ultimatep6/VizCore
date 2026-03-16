# import struct
# import moderngl

# ctx = moderngl.create_context(standalone=True)

# program = ctx.program(
#     vertex_shader="""
#     #version 330

#     // Output values for the shader. They end up in the buffer.
#     out float value;
#     out float product;

#     void main() {
#         // Implicit type conversion from int to float will happen here
#         // gl_VertexID increments from 0 to 9 as the shader runs for each vertex.
#         value = gl_VertexID;
#         product = gl_VertexID * gl_VertexID;
#     }
#     """,
#     # What out varyings to capture in our buffer!
#     varyings=["value", "product"],
# )

# NUM_VERTICES = 10

# # We always need a vertex array in order to execute a shader program.
# # Our shader doesn't have any buffer inputs, so we give it an empty array.
# vao = ctx.vertex_array(program, [])

# # Buffer for 20 floats (10 vertices * 2 varyings per vertex) to hold the output of the shader.
# # Each float is 4 bytes, so we reserve 80 bytes of memory.
# buffer = ctx.buffer(reserve=NUM_VERTICES * 8)

# # Start a transform with buffer as the destination.
# # We force the vertex shader to run 10 times
# vao.transform(buffer, vertices=NUM_VERTICES)

# # Unpack the 20 float values from the buffer (copy from graphics memory to system memory).
# # Reading from the buffer will cause a sync (the python program stalls until the shader is done)
# data = struct.unpack("20f", buffer.read()) # 20 floats 
# for i in range(0, 20, 2):
#     # we read every second value of the data buffer as the "value" and "product" outputs from the shader, and print them.
#     print("value = {}, product = {}".format(*data[i:i+2]))



import moderngl
import numpy as np
from PIL import Image

ctx = moderngl.create_standalone_context()

prog = ctx.program(
    vertex_shader='''
        #version 330
        in vec2 in_vert;
        in vec3 in_color;
        out vec3 v_color;
        void main() {
            v_color = in_color;
            gl_Position = vec4(in_vert, 0.0, 1.0);
        }
    ''',
    fragment_shader='''
        #version 330
        in vec3 v_color;
        out vec3 f_color;
        void main() {
            f_color = v_color;
        }
    ''',
)

# # Triangle vertices (counter-clockwise)
# vertices = np.array([
#     [0.0,  0.8,  1.0, 0.0, 0.0],  # Top vertex, red
#     [-0.8, -0.8, 0.0, 1.0, 0.0],  # Bottom left, green
#     [0.8, -0.8, 0.0, 0.0, 1.0],   # Bottom right, blue
# ], dtype='f4')

# vbo = ctx.buffer(vertices.tobytes())
# vao = ctx.simple_vertex_array(prog, vbo, 'in_vert', 'in_color')

# fbo = ctx.simple_framebuffer((512, 512))
# fbo.use()
# fbo.clear(0.0, 0.0, 0.0, 1.0)
# vao.render(moderngl.TRIANGLES)

# Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1).show()

N = 100
R = 1.0

vert = np.empty((3*N,5),dtype='f4')

dangle = np.pi*2/N
curr = 0
for i in range(0,N):
    x0 = R*np.cos(curr)
    y0 = R*np.sin(curr)
    
    x1 = R*np.cos(curr+dangle)
    y1 = R*np.sin(curr+dangle)

    vert[3*i,:] = [0.0,  0.0,  1.0, 1.0, 1.0]
    vert[3*i+1,:] = [x0,  y0,  1.0, 1.0, 1.0]
    vert[3*i+2,:] = [x1,  y1,  1.0, 1.0, 1.0]

    curr += dangle

vbo = ctx.buffer(vert.tobytes())
vao = ctx.simple_vertex_array(prog, vbo, 'in_vert', 'in_color')

fbo = ctx.simple_framebuffer((512, 512))
fbo.use()
fbo.clear(0.0, 0.0, 0.0, 1.0)
vao.render(moderngl.TRIANGLES)

Image.frombytes('RGB', fbo.size, fbo.read(), 'raw', 'RGB', 0, -1).show()


    


