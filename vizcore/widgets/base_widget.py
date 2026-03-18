class BaseWidget:
    """
    Abstract widget class.

    Responsibilities:
        - Define widget interface
        - Store widget rectangle
        - Maintain widget state

    All widgets must implement:
        - update(data)
        - draw(renderer)
        - resize(rect)
    """
    def __init__(self, rect=None):
        self.rect = rect
        self.state = {}

    def update(self, data):
        raise NotImplementedError("update() must be implemented by subclass")
    
    def draw_lines(self, renderer):
        pass

    def draw_text(self, renderer):
        pass


    def draw(self, renderer):
        raise NotImplementedError("draw() must be implemented by subclass")

    def resize(self, rect):
        self.rect = rect

    def bind_signal(self, data_bus, signal):
        """
        Optionally bind this widget to a signal or signals from the data bus.
        Subclasses should override this if they support signal binding.
        """
        pass

    def bind_renderer(self, renderer):
        pass  # override in widgets that need GPU buffer pre-allocation