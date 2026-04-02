import moderngl
import pyglet

from vizcore.renderer.renderer import Renderer
from vizcore.widget.baseWidget import BaseWidget
from vizcore.renderer.camera import Camera


class Window:
    def __init__(self, application: object, width: int, height: int):
        self.application = application
        self.ctx = application.ctx
        self.width = width
        self.height = height

        self._renderer = Renderer(application, (width, height))

        self._widgets = []

        self.bind_events()

    def set_Texture(self, texture):
        self.texture = texture

    def bind_widget(self, widget:BaseWidget):
        self._widgets.append(widget)
        widget.bind_renderer(self._renderer)
        widget.bind_camera(Camera(self.width, self.height))

    def update(self):
        for widget in self._widgets:
            widget.update()
    
    def render(self):
        for widget in self._widgets:
            widget.draw(self._renderer)

    def on_draw(self):
        self.ctx.clear(0.1, 0.1, 0.1)
        self.update()
        self.render()

    def bind_events(self):
        @self.application.window.event
        def on_draw():
            self.on_draw()

if __name__ == "__main__":
    width, height = 800, 600

    window = pyglet.window.Window(width, height, "Orientation Frame")
    window.switch_to()

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.viewport = (0, 0, width, height)

    app = type('App', (object,), {'ctx': ctx, 'window': window})()

    viz_window = Window(app, width, height)
