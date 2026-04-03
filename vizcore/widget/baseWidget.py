
class BaseWidget:
    """
    Template class for authoring custom visualization widgets.
    
    LIFECYCLE WHEN ADDED TO A TILE:
    1. __init__(...) -> User instantiates the widget.
    2. bind_renderer(renderer) -> Window provides the master renderer (load shaders, alloc buffers here).
    3. bind_camera(camera) -> Window provides a localized Camera mapped exactly to the tile's aspect ratio.
    4. User attaches signals -> bind_external_signal(data_bus, signal_names) is invoked.
    
    RENDER LOOP:
    5. window.update() -> obj.update() -> Pull data from RingBuffers/DataBus and step animations.
    6. window.render() -> obj.draw(renderer) -> Push bound VAOs/VBOs to the GPU.
    """

    def __init__(self, rect=None):
        self.rect = rect
        self.camera = None
        self._renderer = None
        self.data_bus = None

    def accepts_signal(self, data_bus, signal_name) -> bool:
        """
        Validates if a signal matches the strict dimensionality or datatype requirements of this widget.
        The UI uses this to filter dropdown options.
        
        Example override:
            val = data_bus.latest(signal_name)
            return True if np.asarray(val).shape == (1,) else False
        """
        return True
        
    def bind_external_signal(self, data_bus, signal: list):
        """
        Bind this widget to new dynamic signals dynamically attached from the UI.
        
        Args:
            data_bus: DataBus instance providing access to signals.
            signal: List of signal name strings the user requested to attach.
        """
        self.data_bus = data_bus

    def bind_renderer(self, renderer):
        """
        Called automatically by the Window when the widget is dropped into a Tile.
        Initialize your Moderngl VBOs, VAOs, and TextRenderers here!
        """
        self._renderer = renderer

    def bind_camera(self, camera):
        """
        Called automatically by the Window. Provides a Camera customized to this specific Tile's size.
        When the user splits or resizes the tile, the Window will automatically update this Camera's
        internal projection matrix for you.
        """
        self.camera = camera

    def load_shaders(self, shader_manager):
        """
        Load and compile shaders tailored for your widget (if not relying on base Engine shaders).
        """
        pass

    def update(self):
        """
        Called every frame BEFORE drawing. 
        Fetch data from the databus (data_bus.latest(signal)), update physics, animations, or VBO arrays.
        """
        raise NotImplementedError("update() must be implemented by subclass")
    
    def draw(self, renderer):
        """
        Called every frame to push graphics to the mapped GPU viewport.
        Use renderer.draw("shader_name", [(vbo, format, attrs...)], ibo)
        """
        raise NotImplementedError("draw() must be implemented by subclass")