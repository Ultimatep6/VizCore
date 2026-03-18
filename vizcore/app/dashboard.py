from .window import ApplicationWindow
from .mainloop import MainLoop
from ..bus.data_bus import DataBus
from ..renderer.renderer import Renderer
from ..layout.grid_layout import GridLayout
from ..layout.rect import Rect
import pyglet

class Dashboard:
    """
    Main entry point for building dashboards.

    Responsibilities:
        - Manage widget registration
        - Connect to telemetry data bus
        - Initialize renderer
        - Initialize layout engine
        - Start visualization loop

    Primary functionality:
        - Add widgets to layout
        - Bind widgets to telemetry signals
        - Control dashboard lifecycle
    """

    def __init__(self, width=800, height=600, title="VizCore Dashboard", rows=2, cols=2, 
                 fullscreen=False, fullscreen_mode='borderless', screen_index=None):
        """
        Create a dashboard.
        
        Args:
            width: Window width (ignored if fullscreen=True)
            height: Window height (ignored if fullscreen=True)
            title: Window title
            rows: Number of grid rows
            cols: Number of grid columns
            fullscreen: Whether to start in fullscreen mode
            fullscreen_mode: Type of fullscreen
                - 'borderless': Borderless window at screen resolution (RECOMMENDED - most compatible)
                - 'exclusive': True fullscreen with mode switch (may cause blanking on some monitors)
                - 'maximized': Maximized window with borders (safest, but has title bar)
            screen_index: Which screen to use (0=primary, 1=secondary, etc.)
                         None=auto-detect largest screen (usually external monitor)
        """
        # Calculate minimum window size based on grid layout
        # Each cell needs at least 200x150 pixels to be usable
        min_cell_width = 200
        min_cell_height = 150
        min_width = cols * min_cell_width
        min_height = rows * min_cell_height

        # If fullscreen, get actual screen dimensions
        if fullscreen:
            display = pyglet.display.get_display()
            screens = display.get_screens()
            
            if screen_index is not None and 0 <= screen_index < len(screens):
                screen = screens[screen_index]
            else:
                # Auto-detect: use the largest screen
                screen = max(screens, key=lambda s: s.width * s.height)
            
            width = screen.width
            height = screen.height

        # Create window first so we have a valid OpenGL context
        self.window = ApplicationWindow(
            width=width, 
            height=height, 
            title=title,
            fullscreen=fullscreen,
            fullscreen_mode=fullscreen_mode,
            min_width=min_width,
            min_height=min_height,
            screen_index=screen_index
        )
        
        # Now create renderer with the window's context
        self.renderer = Renderer(self.window.ctx, window_size=(width, height))
        
        # Set renderer on window for resize handling
        self.window.renderer = self.renderer
        
        self.data_bus = DataBus()
        self.layout_engine = GridLayout(rows, cols, width, height)
        
        # Connect layout engine to window so resize events propagate
        self.window.layout_engine = self.layout_engine
        self.widgets = []

    def add_widget(self, widget, row=0, col=0, signal=None):
        self.widgets.append(widget)
        if signal:
            widget.bind_signal(self.data_bus, signal)
        self.layout_engine.assign_widget(widget, row, col)
        # Give the widget its rect immediately
        x, y, w, h = self.layout_engine.compute_rect(row, col)
        widget.resize(Rect(x, y, w, h))
        widget.bind_renderer(self.renderer)

    def run(self, signal_source_update=None):
        mainloop = MainLoop(
            self.window, self.widgets,
            renderer=self.renderer,
            layout_engine=self.layout_engine,
            signal_source_update=signal_source_update,
        )
        mainloop.run()