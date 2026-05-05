import numpy as np
import moderngl
from vizcore.widget.baseWidget import BaseWidget

class ScalarGauge(BaseWidget):
    """
    A 2D UI gauge widget for visualizing a single scalar value.
    Renders a horizontal progress bar with dynamic color thresholds and text labels.
    """
    
    def __init__(self, rect=None, min_val=0.0, max_val=100.0, threshold=20.0, text_renderer=None):
        super().__init__(rect)
        
        self.min_val = min_val
        self.max_val = max_val
        self.threshold = threshold
        
        self._text_renderer = text_renderer
        self._renderer = None
        self.camera = None
        
        self.signal_names = []
        self.current_values = {}
        self._vbos = {}
        self.gauge_hitboxes = {}
        self.editing_properties = None
        
        self.gauge_configs = {}
        
        # Default layout if rect is not provided [x, y, width, height]
        self.rect = rect if rect else [50, 50, 200, 30]

    @property
    def required_shape(self):
        """Ensures the widget only accepts scalar values or (1,) shape arrays."""
        return [(1,)]

    def bind_external_signal(self, data_bus, signal: list):
        """Binds the widget to specific 1D scalar signals on the data bus."""
        self.data_bus = data_bus
        for s in signal:
            if s not in self.signal_names:
                self.signal_names.append(s)
                self.current_values[s] = 0.0
                self.gauge_configs[s] = {'min_val': self.min_val, 'max_val': self.max_val, 'threshold': self.threshold}

    def bind_renderer(self, renderer):
        """Binds the main renderer and initializes GPU buffers."""
        self._renderer = renderer
        if not self._text_renderer:
            self._text_renderer = getattr(renderer, 'text_renderer', None)
        self._build_buffers()

    def bind_camera(self, camera):
        self.camera = camera
        
    def get_context_menu(self, local_x, local_y):
        ry = self.camera.height - local_y
        for sig, hbx in getattr(self, 'gauge_hitboxes', {}).items():
            x, y, w, h = hbx
            if x <= local_x <= x + w and y <= ry <= y + h:
                self.selected_gauge = sig
                return [f"Remove {sig}", f"Properties {sig}"]
        self.selected_gauge = None
        return None
        
    def on_context_menu(self, action_label):
        if action_label.startswith("Remove "):
            sig = action_label[7:]
            if sig in self.signal_names:
                self.signal_names.remove(sig)
        elif action_label.startswith("Properties "):
            sig = action_label[11:]
            self.editing_properties = sig
            self.active_slider = None

    def on_mouse_press(self, local_x, local_y, button, modifiers):
        if self.editing_properties and button == 1: # Left click
            w, h = 400, 250
            x = (self.camera.width - w) / 2
            y = (self.camera.height - h) / 2
            ry = self.camera.height - local_y
            
            # Close if clicked outside
            if not (x <= local_x <= x + w and y <= ry <= y + h):
                self.editing_properties = None
                self.active_slider = None
                return
            
            # Clickable slider zones matched to top-left Y coordinates
            sx = x + 20
            sw = 360
            self.active_slider = None
            if sx <= local_x <= sx + sw:
                if y + 70 <= ry <= y + 110:
                    self.active_slider = 'min_val'
                elif y + 130 <= ry <= y + 170:
                    self.active_slider = 'max_val'

    def on_mouse_drag(self, local_x, local_y, dx, dy, buttons, modifiers):
        if getattr(self, 'editing_properties', None) and getattr(self, 'active_slider', None):
            conf = self.gauge_configs[self.editing_properties]
            # Infinite scrolling scale based on dx to handle out-of bounds numbers flexibly
            span = max(10.0, abs(conf['max_val'] - conf['min_val']))
            conf[self.active_slider] += (dx / 250.0) * span

    def on_mouse_release(self, local_x, local_y, button, modifiers):
        if button == 1:
            self.active_slider = None

    def _build_buffers(self):
        """Creates VBOs for rendering the 2D bar."""
        # Unit rectangle for TRIANGLE_STRIP
        quad_verts = np.array([
            0.0, 0.0,  # Bottom Left
            1.0, 0.0,  # Bottom Right
            0.0, 1.0,  # Top Left
            1.0, 1.0,  # Top Right
        ], dtype='f4')
        self._vbos['quad'] = self._renderer.ctx.buffer(quad_verts.tobytes())

        # Unit rectangle for LINE_LOOP (border)
        border_verts = np.array([
            0.0, 0.0,
            1.0, 0.0,
            1.0, 1.0,
            0.0, 1.0
        ], dtype='f4')
        self._vbos['border'] = self._renderer.ctx.buffer(border_verts.tobytes())

    def update(self):
        """Fetches the latest scalar values from the DataBus."""
        if hasattr(self, 'data_bus'):
            for sig in self.signal_names:
                val = self.data_bus.latest(sig)
                if val is not None:
                    # Safely extract the scalar value whether it's a float or a (1,) numpy array
                    self.current_values[sig] = float(np.asarray(val).flatten()[0])

    def draw(self, renderer):
        """Renders the 2D gauge overlays."""
        self.gauge_hitboxes.clear()
        
        if not self.signal_names or 'quad' not in self._vbos or not self.camera:
            return

        # Disable depth testing for 2D UI overlay to prevent Z-fighting with 3D objects
        renderer.ctx.disable(moderngl.DEPTH_TEST)
        
        is_vertical_layout = self.camera.height > self.camera.width
        num_signals = len(self.signal_names)

        renderer.set_uniform("ui", "u_resolution", (self.camera.width, self.camera.height))

        for i, sig in enumerate(self.signal_names):
            val = self.current_values.get(sig, 0.0)
            
            conf = self.gauge_configs.get(sig)
            if conf:
                c_min, c_max, c_thresh = conf['min_val'], conf['max_val'], conf['threshold']
            else:
                c_min, c_max, c_thresh = self.min_val, self.max_val, self.threshold
            
            # 1. Calculate Proportions
            clamped_val = max(c_min, min(val, c_max))
            span = c_max - c_min
            proportion = (clamped_val - c_min) / span if span > 0 else 0.0

            # 2. Determine Dynamic Color Thresholds
            if val <= c_thresh:
                fill_color = (0.85, 0.2, 0.2)  # Red
            else:
                fill_color = (0.2, 0.85, 0.2)  # Green
                
            if not is_vertical_layout:
                # Horizontal blocks scaling downwards
                w = max(10.0, self.camera.width * 0.8)
                available_h = self.camera.height * 0.8
                h_per_bar = available_h / num_signals
                h = max(5.0, h_per_bar * 0.5)
                
                x = (self.camera.width - w) / 2
                y = self.camera.height - (self.camera.height * 0.1) - (i + 1) * h_per_bar + (h_per_bar - h) / 2
                self.gauge_hitboxes[sig] = (x, y, w, h)

                renderer.set_uniform("ui", "u_pos", (x, y))
                
                # 3. Draw Background
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.15, 0.15, 0.15))
                renderer.draw("ui", [(self._vbos["quad"], "2f", "in_vert")], mode=moderngl.TRIANGLE_STRIP)

                # 4. Draw Filled Progress Bar
                renderer.set_uniform("ui", "u_size", (w * proportion, h))
                renderer.set_uniform("ui", "u_color", fill_color)
                renderer.draw("ui", [(self._vbos["quad"], "2f", "in_vert")], mode=moderngl.TRIANGLE_STRIP)

                # 5. Draw Border Frame
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.5, 0.5, 0.5))
                renderer.draw("ui", [(self._vbos['border'], "2f", "in_vert")], mode=moderngl.LINE_LOOP)

                # 6. Render Typography
                if self._text_renderer:
                    text_y = y + h + max(2.0, h_per_bar * 0.1)
                    label_text = f"{sig.split('.')[-1]}: {val:.1f}"
                    text_scale = min(0.45, max(0.2, (h_per_bar * 0.3) / 10.0))
                    self._text_renderer.render_text(label_text, x, text_y, color=(1.0, 1.0, 1.0), scale=text_scale)
            else:
                # Vertical blocks scaling sideways
                h = max(10.0, self.camera.height * 0.8)
                available_w = self.camera.width * 0.8
                w_per_bar = available_w / num_signals
                w = max(5.0, w_per_bar * 0.4)
                
                y = (self.camera.height - h) / 2
                x = self.camera.width * 0.1 + i * w_per_bar + (w_per_bar - w) / 2
                
                self.gauge_hitboxes[sig] = (x, y, w, h)
                
                renderer.set_uniform("ui", "u_pos", (x, y))

                # 3. Draw Background
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.15, 0.15, 0.15))
                renderer.draw("ui", [(self._vbos["quad"], "2f", "in_vert")], mode=moderngl.TRIANGLE_STRIP)

                # 4. Draw Filled Progress Bar (vertically sized based on proportion)
                renderer.set_uniform("ui", "u_size", (w, h * proportion))
                renderer.set_uniform("ui", "u_color", fill_color)
                renderer.draw("ui", [(self._vbos["quad"], "2f", "in_vert")], mode=moderngl.TRIANGLE_STRIP)

                # 5. Draw Border Frame
                renderer.set_uniform("ui", "u_size", (w, h))
                renderer.set_uniform("ui", "u_color", (0.5, 0.5, 0.5))
                renderer.draw("ui", [(self._vbos['border'], "2f", "in_vert")], mode=moderngl.LINE_LOOP)

                # 6. Render Typography
                if self._text_renderer:
                    # Fix vertical label alignment
                    label_text = f"{sig.split('.')[-1]}"
                    val_text = f"{val:.1f}"
                    text_scale = min(0.35, max(0.15, (w_per_bar * 0.4) / 15.0))
                    
                    text_y_label = y + h + max(5.0, self.camera.height * 0.02)
                    text_y_val = y - max(15.0, self.camera.height * 0.05)
                    
                    self._text_renderer.render_text(label_text, x - w * 0.1, text_y_label, color=(1.0, 1.0, 1.0), scale=text_scale)
                    self._text_renderer.render_text(val_text, x - w * 0.1, text_y_val, color=(0.8, 0.9, 0.8), scale=text_scale)

        self._draw_properties_modal(renderer)
        # Re-enable depth testing for the rest of the 3D scene
        renderer.ctx.enable(moderngl.DEPTH_TEST)

    def _draw_properties_modal(self, renderer):
        if not self.editing_properties or 'quad' not in self._vbos or not self.camera:
            return
            
        w, h = 400, 250
        x = (self.camera.width - w) / 2
        y = (self.camera.height - h) / 2

        renderer.set_uniform("ui", "u_pos", (x, y))
        renderer.set_uniform("ui", "u_size", (w, h))
        renderer.set_uniform("ui", "u_color", (0.2, 0.2, 0.25))
        renderer.draw("ui", [(self._vbos["quad"], "2f", "in_vert")], mode=moderngl.TRIANGLE_STRIP)
        
        renderer.set_uniform("ui", "u_color", (0.6, 0.6, 0.6))
        renderer.draw("ui", [(self._vbos['border'], "2f", "in_vert")], mode=moderngl.LINE_LOOP)
        
        if self._text_renderer:
            self._text_renderer.render_text(f"Edit {self.editing_properties.split('.')[-1]}", x + 20, y + 30, color=(1, 1, 1), scale=0.4)
            
            conf = self.gauge_configs[self.editing_properties]

            def _measure_text_bounds(text, scale):
                atlas_chars = self._text_renderer.atlas.characters
                cursor_x = 0.0
                min_x = 0.0
                max_x = 0.0
                min_y = 0.0
                max_y = 0.0
                seen = False

                for ch in text:
                    if ch not in atlas_chars:
                        continue
                    char_info = atlas_chars[ch]
                    gw, gh = char_info['size']
                    ox, oy = char_info['bearing']

                    gw *= scale
                    gh *= scale
                    ox *= scale
                    oy *= scale

                    x0 = cursor_x + ox
                    y0 = -oy
                    x1 = x0 + gw
                    y1 = y0 + gh

                    if not seen:
                        min_x, max_x = x0, x1
                        min_y, max_y = y0, y1
                        seen = True
                    else:
                        min_x = min(min_x, x0)
                        max_x = max(max_x, x1)
                        min_y = min(min_y, y0)
                        max_y = max(max_y, y1)

                    cursor_x += char_info['advance'] * scale

                if not seen:
                    return 0.0, 0.0, 0.0, 0.0
                return min_x, max_x, min_y, max_y
            
            # Helper to draw centered property box
            def draw_property_box(name, val, sy):
                # Faint line across
                renderer.set_uniform("ui", "u_pos", (x + 20, sy + 15))
                renderer.set_uniform("ui", "u_size", (360, 2))
                renderer.set_uniform("ui", "u_color", (0.3, 0.3, 0.3))
                renderer.draw("ui", [(self._vbos["quad"], "2f", "in_vert")], mode=moderngl.TRIANGLE_STRIP)
                
                # Center box
                bw = 200
                bh = 34
                bx = x + (w - bw) / 2
                
                renderer.set_uniform("ui", "u_pos", (bx, sy))
                renderer.set_uniform("ui", "u_size", (bw, bh))
                renderer.set_uniform("ui", "u_color", (0.15, 0.15, 0.15))
                renderer.draw("ui", [(self._vbos["quad"], "2f", "in_vert")], mode=moderngl.TRIANGLE_STRIP)
                
                renderer.set_uniform("ui", "u_color", (0.5, 0.5, 0.5))
                renderer.draw("ui", [(self._vbos['border'], "2f", "in_vert")], mode=moderngl.LINE_LOOP)

                label = f"{name}: {val:.1f}"
                text_scale = 0.28
                min_x, max_x, min_y, max_y = _measure_text_bounds(label, text_scale)
                text_w = max_x - min_x
                text_h = max_y - min_y
                text_x = bx + (bw - text_w) * 0.5 - min_x
                text_y = sy + (bh - text_h) * 0.5 - min_y + 6.0

                return label, text_x, text_y, text_scale

            text_entries = [
                draw_property_box("Min", conf['min_val'], y + 70),
                draw_property_box("Max", conf['max_val'], y + 130),
            ]

            for label, text_x, text_y, text_scale in text_entries:
                self._text_renderer.render_text(label, text_x, text_y, color=(0.9, 0.9, 0.9), scale=text_scale)
            
            self._text_renderer.render_text("[Drag values horizontally to adjust]", x + 20, y + 230, color=(0.7, 0.7, 0.7), scale=0.25)