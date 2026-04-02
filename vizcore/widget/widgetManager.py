class WidgetManager:
    """
    Manages multiple widgets, their data buses, and rendering.
    
    Example usage:
        manager = WidgetManager()
        frame = KinematicFrameWidget(...)
        manager.add_widget(frame)
        
        # In the render loop
        while True:
            manager.update()  # Update all widgets with latest data
            manager.render(model, view, projection)  # Render all widgets
    """
    def __init__(self):
        self.widgets = []

    def push_to_bus(self, data_bus):
        for widget in self.widgets:
            widget.offload(data_bus)

    def add_widget(self, widget, shader_manager=None):
        """Add a widget to the manager and set up its data bus."""
        self.widgets.append(widget)
        if hasattr(widget, 'data_bus'):
            self.data_buses[widget] = widget.data_bus
    
    def load_shaders(self, shader_manager):
        """Load shaders for all widgets that have a load_shaders method."""
        for widget in self.widgets:
            if hasattr(widget, 'load_shaders'):
                widget.load_shaders(shader_manager)

    def update(self):
        """Do all the math for each widget."""
        for widget in self.widgets:
            if hasattr(widget, 'update'):
                widget.update()

    def offload(self, data_bus):
        """Push all the data being stored on CPU to the GPU buffers for each widget."""
        for widget in self.widgets:
            widget.offload(data_bus)

    def render(self, model, view, projection):
        """Render all widgets using the provided model, view, and projection matrices."""
        for widget in self.widgets:
            if hasattr(widget, 'render'):
                widget.render(model, view, projection)