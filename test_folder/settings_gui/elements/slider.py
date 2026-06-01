from guiElement import GUIElement
from guiRenderer import GuiRenderer


class Slider(GUIElement):
    def __init__(self, x, y, w, h, label="", min_val=0.0, max_val=100.0,
                 initial=None, on_change=None):
        super().__init__(x, y, w, h)
        self.label_text = label
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial if initial is not None else (min_val + max_val) / 2
        self.on_change = on_change
        self._dragging = False

    @property
    def ratio(self):
        r = (self.value - self.min_val) / (self.max_val - self.min_val)
        return max(0.0, min(1.0, r))

    def _set_from_x(self, px):
        track_l = self.x + 10
        track_r = self.x + self.w - 10
        rel = (px - track_l) / (track_r - track_l)
        rel = max(0.0, min(1.0, rel))
        self.value = self.min_val + rel * (self.max_val - self.min_val)
        if self.on_change:
            self.on_change(self.value)

    def draw(self, renderer):
        label = f"{self.label_text}: {self.value:.1f}"
        needed = GuiRenderer.text_width(label) + 20
        if needed > self.w:
            self.w = needed

        track_y = self.y + self.h * 0.3
        track_h = max(4, self.h * 0.2)
        renderer.quad(self.x + 10, track_y, self.w - 20, track_h, (0.12, 0.12, 0.12))
        renderer.outline(self.x + 10, track_y, self.w - 20, track_h, (0.3, 0.3, 0.3))
        fill_w = (self.w - 20) * self.ratio
        if fill_w > 1:
            renderer.quad(self.x + 10, track_y, fill_w, track_h, (0.2, 0.6, 0.9))
        thumb_x = self.x + 10 + (self.w - 20) * self.ratio
        thumb_s = 10
        renderer.quad(thumb_x - thumb_s / 2, track_y - 2, thumb_s, track_h + 4, (0.85, 0.85, 0.85))
        renderer.text(label,
                      self.x + 5, self.y + self.h - 8, anchor_x="left", anchor_y="top")
        self.draw_grip(renderer)

    def on_mouse_press(self, x, y, button):
        self._dragging = True
        self._set_from_x(x)

    def on_mouse_drag(self, x, y, dx, dy, buttons):
        if self._dragging:
            self._set_from_x(x)

    def on_mouse_release(self, x, y, button):
        self._dragging = False
