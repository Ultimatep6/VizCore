import pyglet

class MainLoop:
    def __init__(self, window, widgets, target_fps=60,
                 signal_source_update=None, renderer=None, layout_engine=None):
        self.window = window
        self.widgets = widgets
        self.target_fps = target_fps
        self.signal_source_update = signal_source_update
        self.renderer = renderer
        self.layout_engine = layout_engine

    def update(self, dt):
        if self.signal_source_update:
            self.signal_source_update()
        for widget in self.widgets:
            widget.update(None)

    def on_draw(self):
        self.window.clear()
        if self.renderer:
            self.renderer.begin_frame()

            # Pass 1 — all line geometry (viewport changes happen here)
            for widget in self.widgets:
                widget.draw_lines(self.renderer)

            # Pass 2 — all text on top (always full viewport)
            for widget in self.widgets:
                widget.draw_text(self.renderer)

            self.renderer.end_frame()


    def run(self):
        self.window.on_draw = self.on_draw  # override window's on_draw
        pyglet.clock.schedule_interval(self.update, 1.0 / self.target_fps)
        pyglet.app.run()