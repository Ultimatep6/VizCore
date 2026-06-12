import os
import pyglet

from widgets.widget_base import DrawingContext


def measure_text(text_str, font_size=10):
    if not text_str:
        return 0
    lbl = pyglet.text.Label(text_str, font_size=font_size)
    return lbl.content_width


class GuiRenderer:
    def __init__(self, mainWindow):
        self._dc = DrawingContext(
            mainWindow, mainWindow.wnd.width, mainWindow.wnd.height
        )

    @property
    def width(self):
        return self._dc.width

    @width.setter
    def width(self, value):
        self._dc.set_resolution(value, self._dc.height)

    @property
    def height(self):
        return self._dc.height

    @height.setter
    def height(self, value):
        self._dc.set_resolution(self._dc.width, value)

    def set_resolution(self, w, h):
        self._dc.set_resolution(w, h)

    def quad(self, x, y, w, h, color, alpha=1.0):
        self._dc.quad(x, y, w, h, color, alpha)

    def outline(self, x, y, w, h, color, alpha=1.0):
        self._dc.outline(x, y, w, h, color, alpha)

    def text(self, text_str, x, y, color=(1.0, 1.0, 1.0), scale=0.5,
             anchor_x="left", anchor_y="bottom", clip_rect=None):
        self._dc.text(text_str, x, y, color, scale, anchor_x, anchor_y, clip_rect)

    @staticmethod
    def text_width(text_str, scale=0.5):
        """Return the pixel width of *text_str* at the given scale."""
        if not text_str:
            return 0
        font_size = max(1, int(scale * 20))
        return pyglet.text.Label(text_str, font_size=font_size).content_width
