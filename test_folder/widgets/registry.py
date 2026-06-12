"""Widget registry - maps widget names to widget classes."""

from widgets.line_plot import LinePlot


class WidgetRegistry:
    """Simple dict-based registry mapping widget names to widget classes."""

    def __init__(self):
        self._widgets = {}

    def register(self, name, widget_class):
        """Register a widget class with a display name."""
        self._widgets[name] = widget_class

    def get(self, name):
        """Return the widget class for a given name, or None if not found."""
        return self._widgets.get(name)

    def list_names(self):
        """Return a list of all registered widget names."""
        return list(self._widgets.keys())


# Module-level default registry instance
default_registry = WidgetRegistry()

# Register built-in widgets
default_registry.register("Line Plot", LinePlot)