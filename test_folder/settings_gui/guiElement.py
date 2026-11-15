from abc import ABC, abstractmethod


class GUIElement(ABC):
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.visible = True
        self.hovered = False
        self.min_w = 60
        self.min_h = 20
        self._resizing = False
        self._resize_start_w = 0
        self._resize_start_x = 0

    def hit_test(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def hit_test_grip(self, px, py):
        return self.x + self.w - 8 <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def start_resize(self, mx):
        self._resizing = True
        self._resize_start_w = self.w
        self._resize_start_x = mx

    def do_resize(self, mx):
        if not self._resizing:
            return
        self.w = max(self.min_w, self._resize_start_w + int(mx - self._resize_start_x))

    def end_resize(self):
        self._resizing = False

    def draw_grip(self, renderer):
        gx = self.x + self.w - 8
        renderer.outline(gx, self.y, 8, self.h, (0.4, 0.4, 0.4))
        for i in range(3):
            renderer.quad(gx + 2 + i * 2, self.y + 4, 1, self.h - 8, (0.55, 0.55, 0.55))

    @abstractmethod
    def draw(self, renderer):
        pass

    def on_mouse_press(self, x, y, button):
        pass

    def on_mouse_release(self, x, y, button):
        pass

    def on_mouse_drag(self, x, y, dx, dy, buttons):
        pass
