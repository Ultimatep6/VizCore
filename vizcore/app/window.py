import pyglet
import moderngl
from pyglet.window import key

class ApplicationWindow(pyglet.window.Window):
    def __init__(self, width=800, height=600, title="VizCore", 
                 fullscreen=False, renderer=None):
        super().__init__(width=width, height=height, caption=title,
                         resizable=True, fullscreen=fullscreen)

        self.ctx = moderngl.create_context()
        self.layout_engine = None  # Placeholder
        self.widgets = []
        self.renderer = renderer  # Store renderer

    def on_resize(self, width, height):
        super().on_resize(width, height)
        self.ctx.viewport = (0, 0, width, height)
        if self.layout_engine:
            self.layout_engine.on_window_resize(width, height)

    def on_key_press(self, symbol, modifiers):
        for widget in self.widgets:
            widget.handle_key_event(symbol, modifiers)

    def on_draw(self):
        self.clear()
        self.ctx.clear(0.1, 0.1, 0.1)
        for widget in self.widgets:
            if self.renderer:
                widget.draw(self.renderer)

if __name__ == "__main__":
    window = ApplicationWindow()
    pyglet.app.run()