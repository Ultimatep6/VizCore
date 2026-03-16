import pyglet


class MainLoop:
    """
    Controls the render/update loop.

    Responsibilities:
        - Maintain stable frame rate
        - Update widgets
        - Submit draw calls

    Typical loop responsibilities:
        1. Poll window events
        2. Update widgets
        3. Execute rendering pass
    """
    def __init__(self, window, widgets, target_fps=60,
                 signal_source_update=None, renderer=None, layout_engine=None):
        self.window = window
        self.widgets = widgets
        self.target_fps = target_fps
        self.signal_source_update = signal_source_update
        self.renderer = renderer  # add this
        self.layout_engine = layout_engine  # add this
    # rest unchanged

    def update(self, dt):
        # Update signal source first if provided
        if self.signal_source_update:
            self.signal_source_update()
        # Update all widgets (they should pull from their own buffers)
        for widget in self.widgets:
            widget.update(None)
        # Redraw window
        self.window.dispatch_event('on_draw')

    def run(self):
        pyglet.clock.schedule_interval(self.update, 1.0 / self.target_fps)
        pyglet.app.run()