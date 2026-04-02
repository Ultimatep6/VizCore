
class BaseWidget:
    def __init__(self, rect=None):
        self.rect = rect

    def update(self):
        """
        Called each frame to pull latest data from the data bus and update local/GPU buffers.
        Subclasses should override this to implement their update logic.
        """
        raise NotImplementedError("update() must be implemented by subclass")
    
    def draw(self, renderer):
        """
        Called each frame to render the widget using the provided renderer.
        Subclasses should override this to implement their rendering logic.
        """
        raise NotImplementedError("draw() must be implemented by subclass")
    
    def bind_external_signal(self, data_bus, signal):
        """
        Bind this widget to one or more signals from the data bus.
        Subclasses should override this to implement signal binding.
        
        Args:
            data_bus: DataBus instance providing access to signals
            signal: Single signal name (str) or list of signal names
        """
        pass

    def bind_renderer(self, renderer):
        """
        Called once at startup to pre-allocate GPU buffers and create VAOs.
        Subclasses should override this to allocate GPU resources.
        
        Args:
            renderer: Renderer instance for GPU buffer allocation
        """
        pass

    def load_shaders(self, shader_manager):
        """
        Load and compile shaders for the widget.
        Subclasses should override this to load their required shaders.
        
        Args:
            shader_manager: ShaderManager instance for shader compilation
        """
        pass