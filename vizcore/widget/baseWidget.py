
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
        self._bound_signals = set()  # Track currently bound signals

    @property
    def required_shape(self) -> list:
        """
        Defines the list of acceptable NumPy shapes for this widget.
        E.g., [(1,), (3,)] or [(3,3), (4,4)]
        Returns None if the widget accepts any shape.
        """
        return None

    def accepts_signal(self, data_bus, signal_name) -> bool:
        """
        Validates if a signal matches the strict dimensionality requirements of this widget
        by cross-referencing the signal's metadata in the DataBus.
        """
        if self.required_shape is None:
            return True
            
        # Access the DataBus metadata (populated by push_payload)
        with data_bus._lock:
            meta = data_bus._metadata.get(signal_name)
            if meta:
                return meta["shape"] in self.required_shape
        return False
        
    def bind_external_signal(self, data_bus, signal: list):
        """
        Bind this widget to new dynamic signals dynamically attached from the UI.
        
        Args:
            data_bus: DataBus instance providing access to signals.
            signal: List of signal name strings the user requested to attach.
        """
        self.data_bus = data_bus
        
        # Track newly bound signals and notify widget
        for sig in signal:
            if sig not in self._bound_signals:
                self._bound_signals.add(sig)
                self.on_attach_signal(sig)

    def unbind_external_signal(self, data_bus, signal: list):
        """
        Unbind signals from this widget.
        
        Args:
            data_bus: DataBus instance providing access to signals.
            signal: List of signal name strings to unbind.
        """
        for sig in signal:
            if sig in self._bound_signals:
                self._bound_signals.remove(sig)
                self.on_detach_signal(sig)

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

    def on_resize(self, width: int, height: int):
        """
        Called when the widget's tile is resized.
        
        Args:
            width: New width in pixels
            height: New height in pixels
        """
        pass

    def get_context_menu(self, local_x, local_y):
        """
        Return a list of string options for a custom context menu based on the (x, y) click.
        Return None to fallback to the default Window menu.
        """
        return None

    def on_context_menu(self, action_label):
        """
        Handle a click on one of the custom context menu options returned by get_context_menu.
        """
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        """
        Handle mouse press events.
        
        Args:
            x, y: Mouse position in window coordinates
            button: Mouse button pressed (pyglet.window.mouse.LEFT, etc.)
            modifiers: Modifier keys (pyglet.window.key.MOD_SHIFT, etc.)
        """
        pass

    def on_mouse_release(self, x, y, button, modifiers):
        """
        Handle mouse release events.
        
        Args:
            x, y: Mouse position in window coordinates
            button: Mouse button released
            modifiers: Modifier keys
        """
        pass

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        """
        Handle mouse drag events.
        
        Args:
            x, y: Mouse position in window coordinates
            dx, dy: Change in mouse position since last event
            buttons: Mouse buttons currently pressed
            modifiers: Modifier keys
        """
        pass

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        """
        Handle mouse scroll events.
        
        Args:
            x, y: Mouse position in window coordinates
            scroll_x, scroll_y: Scroll amount (typically scroll_y for vertical scroll)
        """
        pass

    def on_attach_signal(self, signal_name: str):
        """
        Called when a new signal is bound to this widget.
        
        Args:
            signal_name: Name of the signal that was bound
        """
        pass

    def on_detach_signal(self, signal_name: str):
        """
        Called when a signal is unbound from this widget.
        
        Args:
            signal_name: Name of the signal that was unbound
        """
        pass

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