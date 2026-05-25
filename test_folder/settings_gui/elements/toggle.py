import pyglet
from guiElement import GUIElement


class Toggle(GUIElement):
    def __init__(self, x, y, w, h, label="", initial=False, on_toggle=None):
        super().__init__(x, y, w, h)
        self.label_text = label
        self.state = initial
        self.on_toggle = on_toggle
        self._label = pyglet.text.Label(
            label, color=(200, 200, 200, 255), anchor_y="center", font_size=10
        )

    def draw(self, renderer):
        bg_color = (0.2, 0.6, 0.2) if self.state else (0.3, 0.3, 0.3)
        renderer.quad(self.x, self.y, self.w, self.h, bg_color)
        renderer.outline(self.x, self.y, self.w, self.h, (0.5, 0.5, 0.5))
        self._label.x = self.x + 8
        self._label.y = self.y + self.h // 2
        self._label.draw()
        state_text = "ON " if self.state else "OFF"
        s = pyglet.text.Label(
            state_text, color=(255, 255, 255, 255),
            anchor_y="center", anchor_x="center", font_size=10
        )
        s.x = self.x + self.w - 28
        s.y = self.y + self.h // 2
        s.draw()
        self.draw_grip(renderer)

    def on_mouse_press(self, x, y, button):
        self.state = not self.state
        if self.on_toggle:
            self.on_toggle(self.state)
