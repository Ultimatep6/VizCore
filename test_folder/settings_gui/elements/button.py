from guiElement import GUIElement
from guiRenderer import GuiRenderer


class Button(GUIElement):
    def __init__(self, x, y, w, h, label, on_click=None,
                 color=(0.3, 0.3, 0.4), hover_color=(0.4, 0.4, 0.5),
                 press_color=(0.2, 0.2, 0.3)):
        super().__init__(x, y, w, h)
        self.label = label
        self.on_click = on_click
        self.color = color
        self.hover_color = hover_color
        self.press_color = press_color
        self.pressed = False

    def draw(self, renderer):
        # Dynamically expand width to fit text
        needed = GuiRenderer.text_width(self.label) + 20
        if needed > self.w:
            self.w = needed

        c = self.press_color if self.pressed else (self.hover_color if self.hovered else self.color)
        renderer.quad(self.x, self.y, self.w, self.h, c)
        renderer.outline(self.x, self.y, self.w, self.h, (0.5, 0.5, 0.5))
        renderer.text(self.label, self.x + self.w // 2, self.y + self.h // 2,
                      anchor_x="center", anchor_y="center")

    def on_mouse_press(self, x, y, button):
        self.pressed = True

    def on_mouse_release(self, x, y, button):
        if self.pressed and self.hovered and self.on_click:
            self.on_click()
        self.pressed = False
