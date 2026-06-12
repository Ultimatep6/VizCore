import os
import numpy as np
import moderngl
import pyglet

from settings import WIDGET_LINE_COLORS

_SHADER_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shaders")


class DrawingContext:
    """
    High-level 2D drawing surface passed to Widget.draw().

    Widget authors use this to render all UI chrome: rectangles,
    outlines, text, and line segments. All coordinates are in pixel
    space relative to the widget's tile, with (0,0) at bottom-left.

    Internally wraps the Renderer and shared GPU
    resources (unit-quad VBOs, ui shader program). Widget authors
    never access the Renderer directly.
    """

    _ui_program = None
    _quad_vbo = None
    _outline_vbo = None
    _quad_vao = None
    _outline_vao = None
    _initialized = False

    def __init__(self, renderer, width, height, offset_x=0, offset_y=0):
        self._renderer = renderer
        self._w = width
        self._h = height
        self._ox = offset_x
        self._oy = offset_y
        DrawingContext._init_shared(renderer.ctx)

    @classmethod
    def _init_shared(cls, ctx):
        if cls._initialized:
            return
        vert_path = os.path.join(_SHADER_DIR, "ui.vert")
        frag_path = os.path.join(_SHADER_DIR, "ui.frag")
        with open(vert_path) as f:
            vert_src = f.read()
        with open(frag_path) as f:
            frag_src = f.read()
        cls._ui_program = ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

        cls._quad_vbo = ctx.buffer(
            np.array([0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype="f4").tobytes()
        )
        cls._outline_vbo = ctx.buffer(
            np.array([0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0], dtype="f4").tobytes()
        )

        cls._quad_vao = ctx.vertex_array(cls._ui_program, [(cls._quad_vbo, "2f", "in_vert")])
        cls._outline_vao = ctx.vertex_array(cls._ui_program, [(cls._outline_vbo, "2f", "in_vert")])

        cls._initialized = True

    def set_resolution(self, w, h):
        self._w = w
        self._h = h

    def set_offset(self, x, y):
        self._ox = x
        self._oy = y

    @property
    def width(self) -> int:
        return self._w

    @property
    def height(self) -> int:
        return self._h

    def quad(self, x, y, w, h, color=(0.5, 0.5, 0.5), alpha=1.0):
        """
        Draw a filled rectangle.

        Args:
            x, y: Bottom-left corner in pixel coordinates.
            w, h: Width and height in pixels.
            color: (r, g, b) tuple of floats in [0, 1].
            alpha: Opacity in [0, 1]. BLEND is always enabled.
        """
        r, g, b = color
        prog = self._ui_program
        prog["u_resolution"] = (self._w, self._h)
        prog["u_pos"] = (self._ox + x, self._oy + y)
        prog["u_size"] = (w, h)
        prog["u_color"] = (r, g, b, alpha)

        self._renderer.ctx.enable(moderngl.BLEND)
        self._renderer.ctx.blend_func = (
            moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
        )

        self._quad_vao.render(moderngl.TRIANGLE_STRIP)

    def outline(self, x, y, w, h, color=(0.8, 0.8, 0.8), alpha=1.0):
        """
        Draw a rectangular outline (no fill).

        Args:
            x, y: Bottom-left corner in pixel coordinates.
            w, h: Width and height in pixels.
            color: (r, g, b) tuple of floats in [0, 1].
            alpha: Opacity in [0, 1].
        """
        r, g, b = color
        prog = self._ui_program
        prog["u_resolution"] = (self._w, self._h)
        prog["u_pos"] = (self._ox + x, self._oy + y)
        prog["u_size"] = (w, h)
        prog["u_color"] = (r, g, b, alpha)

        self._renderer.ctx.enable(moderngl.BLEND)
        self._renderer.ctx.blend_func = (
            moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA,
        )

        self._outline_vao.render(moderngl.LINE_LOOP)

    def h_line(self, y, x1, x2, color=(0.6, 0.6, 0.6), alpha=1.0, thickness=1.0):
        """Draw a horizontal line segment."""
        self.quad(min(x1, x2), y - thickness / 2, abs(x2 - x1), thickness, color, alpha)

    def v_line(self, x, y1, y2, color=(0.6, 0.6, 0.6), alpha=1.0, thickness=1.0):
        """Draw a vertical line segment."""
        self.quad(x - thickness / 2, min(y1, y2), thickness, abs(y2 - y1), color, alpha)

    def text(self, text_str, x, y, color=(1.0, 1.0, 1.0), scale=0.5,
             anchor_x="left", anchor_y="bottom", clip_rect=None):
        if not text_str:
            return
        r, g, b = color[:3]
        ir, ig, ib = int(r * 255), int(g * 255), int(b * 255)
        lbl = pyglet.text.Label(
            text_str,
            color=(ir, ig, ib, 255),
            font_size=max(1, int(scale * 20)),
            anchor_x=anchor_x,
            anchor_y=anchor_y,
            x=int(self._ox + x),
            y=int(self._oy + y),
        )
        lbl.draw()


class Widget:
    """
    Abstract base class for user-contributed visualisation widgets.

    Lifecycle when added to a tile:
        1. setup()              -- one-time initialisation (create components, buffers)
        2. update()             -- every frame: pull data from DataBus
        3. draw(ui)             -- every frame: render using DrawingContext

    Class attributes (override in subclass):
        title (str):            Name shown in context menus.
        transparent (bool):     If True, no solid background is drawn.
        required_shape (list):  List of acceptable NumPy shapes, e.g. [(1,)].
                                None means any shape is accepted.

    Properties available after setup():
        size -> (width, height)   Tile dimensions in pixels.
        read(name) -> value       Latest value from DataBus for signal `name`.

    Context menu:
        get_context_menu() -> list of (label, action) entries.
        action is either a callable (button) or a list of more entries (branch).
    """

    title = "Widget"
    transparent = True
    required_shape = None

    COLORS = list(WIDGET_LINE_COLORS)

    def __init__(self):
        self._tile_x = 0
        self._tile_y = 0
        self._tile_w = 0
        self._tile_h = 0
        self._data_bus = None
        self._drawing_ctx = None
        self._renderer = None
        self._bound_signals = []

    # --- Lifecycle hooks (override in subclass) ---

    def setup(self):
        """
        Called once after the widget is assigned to a tile.

        Create reusable components (Legend, AxisGrid, LineBuffer) here.
        """
        raise NotImplementedError

    def teardown(self):
        """
        Clean up GPU resources and signal bindings.

        Called when the widget is being destroyed. Override in subclass
        to release GPU buffers, detach signals, etc.
        """
        pass

    def update(self):
        """
        Called every frame before draw().

        Pull latest data from the DataBus via self.read(name).
        """
        raise NotImplementedError

    def draw(self, ui: DrawingContext):
        """
        Called every frame. Render the widget using the DrawingContext.

        Args:
            ui: DrawingContext instance.
        """
        raise NotImplementedError

    # --- Input handling (override as needed) ---

    def on_mouse_press(self, x, y, button):
        """Called when a mouse button is pressed inside the tile."""

    def on_mouse_release(self, x, y, button):
        """Called when a mouse button is released inside the tile."""

    def on_mouse_drag(self, x, y, dx, dy, buttons):
        """Called when the mouse is dragged inside the tile."""

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """Called when the mouse wheel is scrolled inside the tile."""

    def on_mouse_move(self, x, y):
        """Called when the mouse moves inside the tile."""

    # --- Public helpers for subclass use ---

    @property
    def size(self):
        """Return the tile dimensions in pixels as (width, height)."""
        return (self._tile_w, self._tile_h)

    def read(self, name):
        """
        Return the latest value for a signal, or None if unavailable.

        Args:
            name: Signal path string (e.g. "sensors.imu.accel_x").
        """
        if self._data_bus is None:
            return None
        return self._data_bus.latest(name)

    def create_line_buffer(self, max_points=1000):
        """
        Allocate a GPU-backed ring buffer for streaming line data.

        Args:
            max_points: Maximum number of data points to buffer.

        Returns:
            LineBuffer instance.
        """
        from components.line_buffer import LineBuffer
        return LineBuffer(self._renderer, max_points)

    def accepts_signal(self, signal_name):
        """Check whether a signal's shape matches this widget's schema."""
        if self.required_shape is None or self._data_bus is None:
            return True
        with self._data_bus._lock:
            meta = self._data_bus._metadata.get(signal_name)
            if meta is None:
                return False
            return meta["shape"] in self.required_shape

    def get_compatible_signals(self):
        """
        Return a list of all DataBus signal paths matching this widget's schema.

        Returns:
            List of signal path strings.
        """
        if self._data_bus is None:
            return []
        if self.required_shape is None:
            return self._data_bus.list_signals()
        paths = []
        for shape in self.required_shape:
            paths.extend(self._data_bus.get_signals_by_shape(shape))
        return paths

    def attach_signal(self, signal_name):
        """Attach a signal. Triggers on_attach_signal()."""
        if signal_name not in self._bound_signals:
            self._bound_signals.append(signal_name)
            self.on_attach_signal(signal_name)

    def detach_signal(self, signal_name):
        """Detach a signal. Triggers on_detach_signal()."""
        if signal_name in self._bound_signals:
            self._bound_signals.remove(signal_name)
            self.on_detach_signal(signal_name)

    def on_attach_signal(self, signal_name):
        """Called when a signal is newly attached. Override in subclass."""

    def on_detach_signal(self, signal_name):
        """Called when a signal is detached. Override in subclass."""

    # --- Context menu ---

    def get_context_menu(self):
        """
        Return context menu entries as a list of (label, action) tuples.

        ``action`` can be:
            - A callable (``lambda: ...``)           → renders as a button
            - A list of more ``(label, action)`` tuples  → renders as a branch

        Override in subclass to provide custom menus.

        The default implementation returns:
            - "Attach Signal" branch (schema-filtered signal tree)
            - "Remove Signal" branch (one entry per bound signal)
        """
        entries = []

        compat = self.get_compatible_signals()
        if compat:
            entries.append(("Attach Signal", self._build_signal_tree(compat)))

        if self._bound_signals:
            entries.append(("Remove Signal", self._build_remove_entries()))

        return entries

    def _build_signal_tree(self, signal_paths):
        """
        Convert flat signal path list into nested (label, action) tree.

        Dot-separated segments become branch nodes; leaf paths become buttons.
        """
        tree = {}
        for path in signal_paths:
            parts = path.split(".")
            node = tree
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            display = parts[-1]
            # Use a tuple to distinguish leaf from branch dicts
            node.setdefault("__leaves", []).append((display, path))

        def _to_entries(subtree):
            entries = []
            for key, val in subtree.items():
                if key == "__leaves":
                    for display, full_path in val:
                        entries.append((display, lambda p=full_path: self.attach_signal(p)))
                else:
                    entries.append((key, _to_entries(val)))
            return entries

        return _to_entries(tree)

    def _build_remove_entries(self):
        """Build remove-signal entries, one per bound signal."""
        entries = []
        for path in self._bound_signals:
            display = path.replace(".", "/")
            entries.append((f"Remove {display}", lambda p=path: self.detach_signal(p)))
        return entries

    # --- Internal lifecycle (called by framework, not widget authors) ---

    def _bind_renderer(self, renderer):
        self._renderer = renderer

    def _bind_drawing_context(self, ctx: DrawingContext):
        self._drawing_ctx = ctx

    def _bind_data_bus(self, data_bus):
        self._data_bus = data_bus

    def _on_tile_resize(self, x, y, w, h):
        self._tile_x = x
        self._tile_y = y
        self._tile_w = w
        self._tile_h = h
        if self._drawing_ctx is not None:
            self._drawing_ctx._ox = x
            self._drawing_ctx._oy = y
            self._drawing_ctx._w = w
            self._drawing_ctx._h = h
