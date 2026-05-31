import numpy as np
from core.signal_schema import SignalSchema


class BaseWidget:
    def __init__(self, rect=None):
        self.rect = rect
        self.camera = None
        self._renderer = None
        self.data_bus = None
        self._bound_signals = set()

    @property
    def signal_schemas(self):
        return None

    @property
    def required_shape(self):
        schemas = self.signal_schemas
        if schemas is None:
            return None
        shapes = []
        for s in schemas:
            if s.shape is not None:
                shapes.append(s.shape)
        return shapes if shapes else None

    @property
    def use_camera(self):
        return False

    def get_camera_config(self):
        return {
            "enable_keyboard": True,
        }

    def accepts_signal(self, data_bus, signal_name):
        schemas = self.signal_schemas
        if schemas is None:
            return True
        meta = data_bus.get_signal_metadata(signal_name)
        if meta is None:
            return False
        sig_schema = meta.get("schema")
        if sig_schema is None:
            if self.required_shape is not None:
                shape = meta.get("shape")
                return shape in self.required_shape
            return True
        return any(s.matches(sig_schema) for s in schemas)

    def validate_signal_value(self, signal_name, value):
        schemas = self.signal_schemas
        if schemas is None:
            return True, []
        for schema in schemas:
            if schema.validators:
                passed, errors = schema.validate(value)
                if not passed:
                    return False, errors
        return True, []

    def bind_external_signal(self, data_bus, signal):
        self.data_bus = data_bus
        for sig in signal:
            if sig not in self._bound_signals:
                if not self.accepts_signal(data_bus, sig):
                    print(f"Warning: Signal '{sig}' does not match widget schema")
                    continue
                value = data_bus.latest(sig)
                if value is not None:
                    passed, errors = self.validate_signal_value(sig, value)
                    if not passed:
                        for err in errors:
                            print(f"Warning: Signal '{sig}' validation failed: {err}")
                        continue
                self._bound_signals.add(sig)
                self.on_attach_signal(sig)

    def unbind_external_signal(self, data_bus, signal):
        for sig in signal:
            if sig in self._bound_signals:
                self._bound_signals.remove(sig)
                self.on_detach_signal(sig)

    def bind_renderer(self, renderer):
        self._renderer = renderer

    def bind_camera(self, camera):
        self.camera = camera

    def on_resize(self, width, height):
        pass

    def get_context_menu(self, local_x, local_y):
        return None

    def on_context_menu(self, action_label):
        pass

    def on_mouse_press(self, x, y, button, modifiers):
        if self.camera and hasattr(self.camera, "on_mouse_press"):
            self.camera.on_mouse_press(button, x, y)

    def on_mouse_release(self, x, y, button, modifiers):
        if self.camera and hasattr(self.camera, "on_mouse_release"):
            self.camera.on_mouse_release(button)

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.camera and hasattr(self.camera, "on_mouse_drag"):
            self.camera.on_mouse_drag(x, y)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        pass

    def on_attach_signal(self, signal_name):
        pass

    def on_detach_signal(self, signal_name):
        pass

    def load_shaders(self, shader_manager):
        pass

    def update(self):
        raise NotImplementedError("update() must be implemented by subclass")

    def draw(self, renderer):
        raise NotImplementedError("draw() must be implemented by subclass")

    @staticmethod
    def transform_vertices(verts, matrix):
        ones = np.ones((len(verts), 1), dtype=np.float32)
        h = np.concatenate([verts, ones], axis=1)
        return (matrix @ h.T).T[:, :3].astype(np.float32)

    @staticmethod
    def colorize_vertices(verts, color):
        colors = np.tile(color, (len(verts), 1)).astype(np.float32)
        return np.concatenate([verts, colors], axis=1)
