"""WidgetManager bridges GUI tile strings to actual Widget instances."""

from types import SimpleNamespace

from widgets.widget_base import DrawingContext
from widgets.widget_gui import MenuRenderer
from widgets.registry import default_registry
from vizcore.renderer.renderer import Renderer


class WidgetManager:
    """
    Bridges the gap between GUI (widget names as strings on tiles) and
    actual Widget instances. Owns widget lifecycle, rendering, event
    forwarding, and DataBus connectivity.
    """

    def __init__(self, mainWindow, data_bus, registry=None):
        """
        Args:
            mainWindow: Application window with ``.ctx`` and ``.wnd`` attributes.
            data_bus: DataBus instance for signal streaming.
            registry: Optional WidgetRegistry (defaults to ``default_registry``).
        """
        self._main_window = mainWindow
        self._data_bus = data_bus
        self._registry = registry or default_registry
        self._widgets = {}  # (x, y) -> Widget instance

        # Determine window size robustly
        wnd = getattr(mainWindow, "wnd", None)
        if wnd is not None:
            size = getattr(wnd, "size", (1280, 720))
            w = getattr(wnd, "width", size[0])
            h = getattr(wnd, "height", size[1])
        else:
            w, h = 1280, 720

        # Create internal Renderer
        app = SimpleNamespace(
            ctx=mainWindow.ctx,
            window=SimpleNamespace(width=w, height=h),
        )
        self._renderer = Renderer(app, (w, h))

        # Create internal DrawingContext (window-sized prototype)
        self._drawing_ctx = DrawingContext(self._renderer, int(w), int(h))

        # Menu renderer for context menus
        self._menu_renderer = MenuRenderer(int(h), int(w))
        self._menu_tile_key = None

    def list_names(self):
        """Return registered widget names from the widget registry."""
        return self._registry.list_names()

    # -----------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------

    def add_widget(self, tile, name):
        """
        Instantiate a widget via the registry, bind renderer/context/DataBus,
        and call setup().

        Tile coordinates are stored directly (bottom-up).
        """
        widget_class = self._registry.get(name)
        if widget_class is None:
            raise ValueError(f"Widget '{name}' not found in registry")

        widget = widget_class()

        # Create per-tile DrawingContext
        ctx = DrawingContext(self._renderer, int(tile.width), int(tile.height), offset_x=int(tile.x), offset_y=int(tile.y))

        # Wiring pattern from test_lineplot.py
        widget._bind_renderer(self._renderer)
        widget._bind_drawing_context(ctx)
        widget._bind_data_bus(self._data_bus)
        widget._on_tile_resize(int(tile.x), int(tile.y), int(tile.width), int(tile.height))
        widget.setup()

        key = (tile.x, tile.y)
        self._widgets[key] = widget
        return widget

    def destroy_widget(self, tile):
        """Remove the widget instance associated with *tile*."""
        key = (tile.x, tile.y)
        widget = self._widgets.pop(key, None)
        if widget is not None:
            widget.teardown()

    # -----------------------------------------------------------------
    # Frame updates
    # -----------------------------------------------------------------

    def update_all(self):
        """Call ``update()`` on every active widget."""
        for widget in self._widgets.values():
            widget.update()

    def render_all(self):
        """
        Iterate active widgets, reuse cached DrawingContext from setup, and
        call ``widget.draw(ctx)``.

        The cached DC already has tile offset baked in. We temporarily set
        resolution to window size so the shader maps absolute pixel coordinates
        to NDC correctly.
        """
        window_w = getattr(getattr(self._main_window, "wnd", None), "width", 1280)
        window_h = getattr(getattr(self._main_window, "wnd", None), "height", 720)

        for widget in self._widgets.values():
            ctx = widget._drawing_ctx
            if ctx is not None:
                ctx.set_resolution(window_w, window_h)
                widget.draw(ctx)

    # -----------------------------------------------------------------
    # Input forwarding
    # -----------------------------------------------------------------

    def _find_widget_at(self, x, y):
        """Return the widget whose tile contains screen coordinates *(x, y)*."""
        for widget in self._widgets.values():
            tx, ty = widget._tile_x, widget._tile_y
            tw, th = widget._tile_w, widget._tile_h
            if tx <= x <= tx + tw and ty <= y <= ty + th:
                return widget
        return None

    def on_mouse_press(self, x, y, button):
        """Forward mouse press to the widget under the cursor."""
        # Menu takes priority when visible
        if self._menu_renderer.visible:
            self._menu_renderer.on_mouse_press(x, y, button)
            return

        widget = self._find_widget_at(x, y)
        if widget:
            widget.on_mouse_press(
                x - widget._tile_x, y - widget._tile_y, button
            )

    def on_mouse_release(self, x, y, button):
        """Forward mouse release to the widget under the cursor."""
        if self._menu_renderer.visible:
            self._menu_renderer.on_mouse_release(x, y, button)
            return

        widget = self._find_widget_at(x, y)
        if widget:
            widget.on_mouse_release(
                x - widget._tile_x, y - widget._tile_y, button
            )

    def on_mouse_drag(self, x, y, dx, dy, buttons):
        """Forward mouse drag to the widget under the cursor."""
        if self._menu_renderer.visible:
            return

        widget = self._find_widget_at(x, y)
        if widget:
            widget.on_mouse_drag(
                x - widget._tile_x,
                y - widget._tile_y,
                dx,
                dy,
                buttons,
            )

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """Forward mouse scroll to the widget under the cursor."""
        if self._menu_renderer.visible:
            return

        widget = self._find_widget_at(x, y)
        if widget:
            widget.on_mouse_scroll(
                x - widget._tile_x, y - widget._tile_y, scroll_x, scroll_y
            )

    def on_mouse_move(self, x, y):
        """Forward mouse move to the widget under the cursor."""
        if self._menu_renderer.visible:
            return

        widget = self._find_widget_at(x, y)
        if widget:
            widget.on_mouse_move(
                x - widget._tile_x, y - widget._tile_y
            )

    # -----------------------------------------------------------------
    # Context menus
    # -----------------------------------------------------------------

    def open_context_menu(self, tile, screen_x, screen_y):
        """
        Open the context menu for the widget on *tile*.
        """
        key = (tile.x, tile.y)
        widget = self._widgets.get(key)
        if widget is None:
            return

        entries = widget.get_context_menu()
        if entries:
            self._menu_renderer.open(entries, screen_x, screen_y)
            self._menu_tile_key = key

    def close_context_menu(self):
        """Close any open context menu."""
        self._menu_renderer.close()
        self._menu_tile_key = None

    def is_menu_open(self):
        """Return True if a context menu is currently visible."""
        return self._menu_renderer.visible

    def draw_menu(self, ui):
        """Render the active context menu using *ui* (DrawingContext)."""
        if not self._menu_renderer.visible:
            return
        window_w = getattr(getattr(self._main_window, "wnd", None), "width", 1280)
        window_h = getattr(getattr(self._main_window, "wnd", None), "height", 720)
        ui.set_resolution(window_w, window_h)
        commands = self._menu_renderer.get_render_commands()
        for cmd in commands:
            if cmd['type'] == 'quad':
                ui.quad(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'], cmd.get('alpha', 1.0))
            elif cmd['type'] == 'outline':
                ui.outline(cmd['x'], cmd['y'], cmd['w'], cmd['h'], cmd['color'], cmd.get('alpha', 1.0))
            elif cmd['type'] == 'text':
                ui.text(cmd['text'], cmd['x'], cmd['y'], color=cmd.get('color', (1.0, 1.0, 1.0)), scale=cmd.get('scale', 0.5), anchor_x=cmd.get('anchor_x', 'left'), anchor_y=cmd.get('anchor_y', 'bottom'))

    def on_resize(self, width, height):
        """Propagate window resize to all widgets and update internal renderer."""
        self._renderer.application.window.width = width
        self._renderer.application.window.height = height
        self._drawing_ctx.set_resolution(width, height)
        for widget in self._widgets.values():
            if widget._drawing_ctx is not None:
                widget._drawing_ctx.set_resolution(width, height)

    def on_menu_mouse_move(self, x, y):
        """Forward mouse-move events to the menu renderer."""
        self._menu_renderer.on_mouse_move(x, y)
