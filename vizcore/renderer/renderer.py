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
        # Submit draw calls for line plot objects
        # This is a stub; actual implementation should render the line plot using points and color.
        pass

    def draw_ui_primitive(self, primitive):
        # Submit draw calls for UI primitives
        primitive.render(self.ctx)

    def begin_frame(self):
        # Prepare GPU state for new frame
        self.ctx.clear(0.1, 0.1, 0.1)

    def end_frame(self):
        # Finalize frame, swap buffers if needed
        pass