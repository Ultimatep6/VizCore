import pyglet
import moderngl


from vizcore.renderer.renderer import Renderer
from vizcore.renderer.camera import Camera
from vizcore.bus.data_bus import DataBus
from vizcore.text.fontAtlas import FontAtlas, TextRenderer


class MockApp:
    def __init__(self, window, ctx):
        self.window = window
        self.ctx = ctx


class WidgetTester:
    """
    A minimalist mock harness to develop and test a single VizCore widget 
    without the complexity of the TileManager, explicit layouts, or full Simulation loops.
    """
    def __init__(self, width=800, height=600, title="Widget Tester"):
        self.window = pyglet.window.Window(width, height, title, resizable=True)
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.DEPTH_TEST)
        
        # Dependency Injection / Mocks
        self.app = MockApp(self.window, self.ctx)
        self.renderer = Renderer(self.app, (width, height))
        self.camera = Camera(width, height)
        self.data_bus = DataBus()
        self.widget = None

        # Text rendering setup mock
        try:
            self.atlas = FontAtlas(font_path="vizcore/text/data/cmunbi.ttf", font_size=48)
            window_wrapper = type('Window', (), {
                'ctx': self.ctx, 
                'size': (width, height),
                'texture': None
            })()
            self.renderer.text_renderer = TextRenderer(window=window_wrapper, atlas=self.atlas)
        except Exception as e:
            print(f"Warning: Failed to load TextRenderer: {e}")

        # Load common UI shader that widgets expect the window to normally have initialized
        try:
            self.renderer.shader_manager.load_shader(
                "ui",
                vertex_path="vizcore/renderer/shaders/ui.vert",
                fragment_path="vizcore/renderer/shaders/ui.frag"
            )
        except Exception as e:
            print(f"Warning: Failed to load basic 'ui' shader: {e}")

    def set_widget(self, widget):
        self.widget = widget
        # Fire standard window binding callbacks
        self.widget.bind_renderer(self.renderer)
        self.widget.bind_camera(self.camera)

    def register_signal(self, name, size=None):
        self.data_bus.register_signal(name, size)

    def push_data(self, name, value):
        self.data_bus.push(name, value)

    def run(self, mock_update_fn=None):
        """ Runs the isolated application loop """
        if mock_update_fn:
            pyglet.clock.schedule_interval(mock_update_fn, 1/60.0)

        @self.window.event
        def on_draw():
            self.ctx.viewport = (0, 0, self.window.width, self.window.height)
            self.ctx.clear(0.1, 0.1, 0.1, 1.0)
            
            if self.widget:
                self.widget.update()
                self.widget.draw(self.renderer)

        @self.window.event
        def on_resize(width, height):
            # Ensure the GPU viewport and camera matrices update live while testing layouts
            self.ctx.viewport = (0, 0, width, height)
            self.camera.update_projection(max(1, width), max(1, height))

        print("--- Widget Tester Active ---")
        print("Close the window to exit.")
        pyglet.app.run()
