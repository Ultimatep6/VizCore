
from .window import ApplicationWindow
from .mainloop import MainLoop
from ..bus.data_bus import DataBus
from ..renderer.renderer import Renderer
from ..layout.grid_layout import GridLayout

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

    def __init__(self, width=800, height=600, title="VizCore Dashboard", rows=2, cols=2):
        self.window = ApplicationWindow(width=width, height=height, title=title)
        self.data_bus = DataBus()
        # Create ModernGL context from window (assume window provides a ctx property or similar)
        self.renderer = Renderer(self.window.ctx)
        self.layout_engine = GridLayout(rows, cols, width, height)
        self.widgets = []


    def add_widget(self, widget, row=0, col=0, signal=None):
        self.widgets.append(widget)
        if signal:
            widget.bind_signal(self.data_bus, signal)
        self.layout_engine.assign_widget(widget, row, col)

    def run(self):
        # Optionally initialize renderer and layout engine here
        # Pass renderer and layout_engine to MainLoop if needed
        mainloop = MainLoop(self.window, self.widgets, renderer=self.renderer, layout_engine=self.layout_engine)
        mainloop.run()
