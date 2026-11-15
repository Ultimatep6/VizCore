from settings_gui.guiElement import GUIElement
from settings_gui.guiRenderer import GuiRenderer


class Branch(GUIElement):
    def __init__(self, x, y, w, h, label, sub_factory=None,
                 color=(0.3, 0.3, 0.4), hover_color=(0.4, 0.4, 0.5),
                 press_color=(0.2, 0.2, 0.3)):
        super().__init__(x, y, w, h)
        self.label = label
        self.sub_factory = sub_factory
        self.color = color
        self.hover_color = hover_color
        self.press_color = press_color
        self.pressed = False

    def draw(self, renderer):
        # Dynamically expand width to fit label + ">" arrow
        needed = GuiRenderer.text_width(self.label) + 30
        if needed > self.w:
            self.w = needed

        c = self.press_color if self.pressed else (self.hover_color if self.hovered else self.color)
        renderer.quad(self.x, self.y, self.w, self.h, c)
        renderer.outline(self.x, self.y, self.w, self.h, (0.5, 0.5, 0.5))
        renderer.text(self.label, self.x + self.w // 2 - 5, self.y + self.h // 2,
                      anchor_x="center", anchor_y="center")
        renderer.text(">", self.x + self.w - 12, self.y + self.h // 2,
                      anchor_x="center", anchor_y="center")

    def on_mouse_press(self, x, y, button):
        self.pressed = True

    def on_mouse_release(self, x, y, button):
        self.pressed = False
