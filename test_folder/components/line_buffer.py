import os
import numpy as np
import moderngl

_SHADER_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "shaders"
)


class LineBuffer:
    """
    GPU-accelerated ring buffer for streaming line-plot data.

    Manages a ModernGL VBO and index buffer under the hood.
    Widget authors simply call push() and draw().

    Usage in Widget.setup()::

        self.buffer = self.create_line_buffer(max_points=1000)

    Usage in Widget.draw()::

        self.buffer.draw(ui, x, y, w, h, y_min, y_max, color)
    """

    def __init__(self, renderer, max_points=1000):
        """
        Args:
            renderer: vizcore.renderer.renderer.Renderer instance (internal).
            max_points: Number of data points to buffer.
        """
        self._renderer = renderer
        self._max_points = max_points
        self._count = 0

        # CPU-side ring buffer
        self._data = np.zeros(max_points, dtype="f4")
        self._indices = np.arange(max_points, dtype="f4")

        # GPU VBO for data values
        self._vbo = renderer.ctx.buffer(reserve=self._data.nbytes)
        # GPU index buffer
        self._ibo = renderer.ctx.buffer(self._indices.tobytes())

        sm = renderer.shader_manager
        vert_path = os.path.join(_SHADER_DIR, "line_plot.vert")
        frag_path = os.path.join(_SHADER_DIR, "line_plot.frag")
        if sm.get_shader("line_plot") is not None:
            del sm._cache["line_plot"]
        sm.load_shader("line_plot", vertex_path=vert_path, fragment_path=frag_path)

    @property
    def range(self):
        """
        Return (min, max) of valid buffered data, or (None, None) if empty.
        """
        if self._count == 0:
            return (None, None)
        valid = self._data[-self._count:]
        return (float(valid.min()), float(valid.max()))

    def push(self, value):
        """
        Append a single value to the ring buffer.

        Args:
            value: Float data point.
        """
        self._data = np.roll(self._data, -1)
        self._data[-1] = float(value)
        self._count = min(self._count + 1, self._max_points)

    def draw(self, ui, x, y, w, h, y_min, y_max, color):
        """
        Render the buffered data as a line strip within the plot rectangle.

        Args:
            ui: DrawingContext (used for resolution info, but draws via
                the line_plot shader internally).
            x, y, w, h: Plot region bounding box in pixel coords.
            y_min, y_max: Y-axis range for normalisation.
            color: (r, g, b) tuple of floats in [0, 1].
        """
        n = self._count
        if n < 2:
            return

        renderer = self._renderer

        # Upload only the valid portion of data
        upload_data = self._data[-n:]
        self._vbo.write(upload_data.tobytes())

        renderer.set_uniform("line_plot", "u_min", y_min)
        renderer.set_uniform("line_plot", "u_max", y_max)
        renderer.set_uniform("line_plot", "u_plot_x", float(x))
        renderer.set_uniform("line_plot", "u_plot_y", float(y))
        renderer.set_uniform("line_plot", "u_plot_width", float(w))
        renderer.set_uniform("line_plot", "u_plot_height", float(h))
        renderer.set_uniform("line_plot", "u_resolution", (ui.width, ui.height))
        renderer.set_uniform("line_plot", "u_points_per_channel", float(n))
        renderer.set_uniform("line_plot", "u_color", color)

        content = [
            (self._vbo, "1f", "in_y_val"),
            (self._ibo, "1f", "in_index"),
        ]

        renderer.draw(
            "line_plot",
            content,
            mode=moderngl.LINE_STRIP,
            vertices=n,
            first=0,
        )
