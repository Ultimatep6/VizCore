import pyglet

from guiRenderer import GuiRenderer
from elements import Button


class BlipGui:
    def __init__(self, mainWindow):
        self.renderer = GuiRenderer(mainWindow)
        self._win_w = mainWindow.wnd.width
        self._win_h = mainWindow.wnd.height
        self.visible = False
        self._elements = []
        self._captured = None
        self._x = 0
        self._y = 0
        self._node_name = ""
        self._name_label = None

    def _flip(self, y):
        return self._win_h - y

    def show(self, x, y, node_name):
        self._x = x
        self._y = self._flip(y)
        self._node_name = node_name
        self.visible = True
        self._captured = None
        self._build()

    def close(self):
        self.visible = False
        self._elements = []
        self._captured = None
        self._name_label = None

    def _build(self):
        y_off = self._y - 35
        self._name_label = pyglet.text.Label(
            self._node_name,
            color=(200, 200, 200, 255),
            anchor_y="top",
            anchor_x="left",
            font_size=12,
            x=self._x + 10,
            y=y_off,
        )
        self._label_y_top = y_off
        self._elements = [
            Button(
                self._x + 10,
                y_off - 55,
                140,
                28,
                "Print Blip",
                on_click=lambda n=self._node_name: print(f"Blip: {n}"),
            ),
        ]

    def _bounds(self):
        if not self._elements:
            return (self._x, self._y - 80, 160, 80)
        pad = 10
        min_x = min(e.x for e in self._elements) - pad
        min_y = min(e.y for e in self._elements) - pad
        max_x = max(e.x + e.w for e in self._elements) + pad
        max_y = self._label_y_top + pad
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def render(self):
        if not self.visible:
            return
        bx, by, bw, bh = self._bounds()
        self.renderer.quad(bx, by, bw, bh, (0.2, 0.2, 0.25))
        self.renderer.outline(bx, by, bw, bh, (0.4, 0.4, 0.5))
        if self._name_label is not None:
            self._name_label.draw()
        for e in self._elements:
            if e.visible:
                e.draw(self.renderer)

    def on_mouse_press(self, x, y, button):
        if not self.visible:
            return False
        fy = self._flip(y)
        bx, by, bw, bh = self._bounds()
        if bx <= x <= bx + bw and by <= fy <= by + bh:
            for e in reversed(self._elements):
                if e.hit_test(x, fy):
                    e.on_mouse_press(x, fy, button)
                    self._captured = e
                    return True
            return True
        self.close()
        return True

    def on_mouse_release(self, x, y, button):
        if self._captured:
            self._captured.on_mouse_release(x, self._flip(y), button)
            self._captured = None

    def on_resize(self, width, height):
        self._win_w = width
        self._win_h = height
        self.renderer.width = width
        self.renderer.height = height
