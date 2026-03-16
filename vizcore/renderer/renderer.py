import moderngl

class Renderer:
    """
    Central rendering controller.

    Responsibilities:
        - Manage render pipeline
        - Submit draw calls
        - Maintain global GPU state

    Capabilities:
        - Draw meshes
        - Draw line plots
        - Draw UI primitives
    """
    def __init__(self, ctx: moderngl.Context):
        self.ctx = ctx
        # Initialize shaders, buffers, and GPU state here

    def draw_mesh(self, mesh):
        # Submit draw calls for mesh objects
        mesh.render(self.ctx)

    def draw_line_plot(self, points, color=(0, 200, 255, 255)):
        # points: flat float32 array [x0,y0, x1,y1, ...]
        # Requires a compiled line shader — see shader_manager
        if len(points) < 4:
            return
        prog = self.shader_manager.get_shader('line_plot')
        if prog is None:
            return
        vbo = self.ctx.buffer(points.astype('f4').tobytes())
        vao = self.ctx.simple_vertex_array(prog, vbo, 'in_vert')
        norm_color = tuple(c / 255.0 for c in color)
        prog['u_color'].value = norm_color
        vao.render(moderngl.LINE_STRIP)
        vbo.release()


    def draw_ui_primitive(self, primitive):
        # Submit draw calls for UI primitives
        primitive.render(self.ctx)

    def begin_frame(self):
        # Prepare GPU state for new frame
        self.ctx.clear(0.1, 0.1, 0.1)

    def end_frame(self):
        # Finalize frame, swap buffers if needed
        pass