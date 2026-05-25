import pyglet
from guiElement import GUIElement


class Branch(GUIElement):
    def __init__(self, x, y, w, h, label, sub_factory=None,
                 color=(0.3, 0.3, 0.4), hover_color=(0.4, 0.4, 0.5),
                 press_color=(0.2, 0.2, 0.3), text_color=(255, 255, 255, 255)):
        super().__init__(x, y, w, h)
        self.label = label
        self.sub_factory = sub_factory
        self.color = color
        self.hover_color = hover_color
        self.press_color = press_color
        self.pressed = False
        self._label = pyglet.text.Label(
            label, color=text_color, anchor_y="center", anchor_x="center", font_size=10
        )

    def draw(self, renderer):
        c = self.press_color if self.pressed else (self.hover_color if self.hovered else self.color)
        renderer.quad(self.x, self.y, self.w, self.h, c)
        renderer.outline(self.x, self.y, self.w, self.h, (0.5, 0.5, 0.5))
        self._label.x = self.x + self.w // 2 - 5
        self._label.y = self.y + self.h // 2
        self._label.draw()
        gt = pyglet.text.Label(">", color=(200, 200, 200, 255), anchor_y="center", font_size=10)
        gt.x = self.x + self.w - 12
        gt.y = self.y + self.h // 2
        gt.draw()
        self.draw_grip(renderer)

    def on_mouse_press(self, x, y, button):
        self.pressed = True

    def on_mouse_release(self, x, y, button):
        self.pressed = False
