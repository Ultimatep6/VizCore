from guiElement import GUIElement
from guiRenderer import GuiRenderer


class Toggle(GUIElement):
    def __init__(self, x, y, w, h, label="", initial=False, on_toggle=None):
        super().__init__(x, y, w, h)
        self.label_text = label
        self.state = initial
        self.on_toggle = on_toggle

    def draw(self, renderer):
        # Dynamically expand width to fit label + ON/OFF
        label_w = GuiRenderer.text_width(self.label_text)
        needed = label_w + 60
        if needed > self.w:
            self.w = needed

        bg_color = (0.2, 0.6, 0.2) if self.state else (0.3, 0.3, 0.3)
        renderer.quad(self.x, self.y, self.w, self.h, bg_color)
        renderer.outline(self.x, self.y, self.w, self.h, (0.5, 0.5, 0.5))
        renderer.text(self.label_text, self.x + 8, self.y + self.h // 2,
                      anchor_x="left", anchor_y="center")
        state_text = "ON" if self.state else "OFF"
        renderer.text(state_text, self.x + self.w - 28, self.y + self.h // 2,
                      anchor_x="center", anchor_y="center")
        self.draw_grip(renderer)

    def on_mouse_press(self, x, y, button):
        self.state = not self.state
        if self.on_toggle:
            self.on_toggle(self.state)
