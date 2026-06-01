"""
Self-contained context menu system for widgets.

The widget returns a simple nested data structure from
``get_context_menu()`` — a list of ``(label, action)`` tuples
where ``action`` is either a callable (button) or a list of
more tuples (branch). This file provides the renderer and
interaction handler for such menus.

No dependencies on ``settings_gui/``.
"""

import pyglet


def _text_width(text, font_size=10):
    if not text:
        return 0
    return pyglet.text.Label(text, font_size=font_size).content_width


class _MenuItem:
    """A positioned menu item — either a button or a branch pivot."""

    ITEM_W = 170
    ITEM_H = 28
    ITEM_GAP = 7

    def __init__(self, x, y, label, action):
        """
        Args:
            x, y: Position in bottom-up coords (y=0 at bottom).
            label: Display text.
            action: Callable (button) or list of (label, action) (branch).
        """
        self.x = x
        self.y = y
        tw = _text_width(label) + 16
        self.w = tw if tw > self.ITEM_W else self.ITEM_W
        self.h = self.ITEM_H
        self.label = label
        self.action = action
        self.hovered = False
        self.pressed = False
        self._sub_items = None  # cached for branches

    def hit_test(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    @property
    def is_branch(self):
        return isinstance(self.action, list)

    @property
    def sub_items(self):
        if not self.is_branch:
            return []
        gap = self.ITEM_H + self.ITEM_GAP
        n = len(self.action)
        return [
            _MenuItem(0, (n - 1 - i) * gap, lbl, act)
            for i, (lbl, act) in enumerate(self.action)
        ]

    def draw(self, ui, win_h):
        # Dynamically expand width to fit text + branch arrow
        needed = _text_width(self.label) + 16
        if self.is_branch:
            needed += 12
        if needed > self.w:
            self.w = needed

        bg = (0.35, 0.35, 0.45) if self.hovered else (0.25, 0.25, 0.35)
        ui.quad(self.x, self.y, self.w, self.h, bg)
        ui.outline(self.x, self.y, self.w, self.h, (0.5, 0.5, 0.5))

        ui.text(self.label, self.x + 8, self.y + self.h // 2,
                anchor_x="left", anchor_y="center")

        if self.is_branch:
            ui.text(">", self.x + self.w - 12, self.y + self.h // 2,
                    anchor_x="center", anchor_y="center")


class MenuRenderer:
    """
    Renders and manages interaction for a nested context menu.

    Usage::

        renderer = MenuRenderer(window_height)

        # On right-click:
        entries = widget.get_context_menu()   # list of (label, action)
        renderer.open(entries, screen_x, screen_y)

        # In render loop:
        renderer.draw(ui)

        # In event handlers:
        renderer.on_mouse_press(x, y, button)
        renderer.on_mouse_release(x, y, button)
        renderer.on_mouse_move(x, y)
    """

    PAD = 10

    def __init__(self, window_height, window_width=None):
        """
        Args:
            window_height: Window height in pixels.
            window_width: Window width in pixels (defaults to 16:9 from height).
        """
        self._win_h = window_height
        self._win_w = window_width or int(window_height * 16 / 9)
        self._top_items = []
        self._sub_levels = []  # list of {"items": list[_MenuItem], "parent": _MenuItem}
        self._captured = None
        self._sub_direction = None  # "right" or "left" — maintained across nested levels
        self.visible = False

    def _flip(self, y):
        return self._win_h - y

    def open(self, entries, screen_x, screen_y):
        """
        Open a context menu from widget entries.

        Args:
            entries: List of (label, action) tuples from Widget.get_context_menu().
            screen_x, screen_y: Right-click screen position (top-down from window).
        """
        bu_y = self._flip(screen_y)  # top-down → bottom-up
        gap = _MenuItem.ITEM_H + _MenuItem.ITEM_GAP
        self._top_items = [
            _MenuItem(screen_x + 10, bu_y - i * gap, lbl, act)
            for i, (lbl, act) in enumerate(entries)
        ]
        self._sub_levels = []
        self._captured = None
        self._sub_direction = None
        self.visible = True
        self._clamp(self._top_items)

    def close(self):
        self.visible = False
        self._top_items = []
        self._sub_levels = []
        self._captured = None
        self._sub_direction = None

    def _clamp(self, items):
        if not items:
            return
        bx, by, bw, bh = self._bounds(items)
        dx = dy = 0
        if by < 0:
            dy = -by
        elif by + bh > self._win_h:
            dy = self._win_h - (by + bh)
        if bx + bw > self._win_w:
            dx = self._win_w - (bx + bw)
        if bx + dx < 0:
            dx = -bx
        if dx or dy:
            for e in items:
                e.x += dx
                e.y += dy

    def _clear_hover(self):
        for item in self._top_items:
            item.hovered = False
        for level in self._sub_levels:
            for item in level["items"]:
                item.hovered = False

    def _bounds(self, items):
        if not items:
            return (0, 0, 0, 0)
        min_x = min(e.x for e in items) - self.PAD
        min_y = min(e.y for e in items) - self.PAD
        max_x = max(e.x + e.w for e in items) + self.PAD
        max_y = max(e.y + e.h for e in items) + self.PAD
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    # ---- Drawing ----

    def draw(self, ui):
        if not self.visible:
            return

        # Top level — bounds already in bottom-up, pass directly to DC
        bx, by, bw, bh = self._bounds(self._top_items)
        ui.quad(bx, by, bw, bh, (0.18, 0.18, 0.22), 0.95)
        ui.outline(bx, by, bw, bh, (0.4, 0.4, 0.5))
        for item in self._top_items:
            item.draw(ui, self._win_h)

        # Sub-levels
        for level in self._sub_levels:
            lbx, lby, lbw, lbh = self._bounds(level["items"])
            ui.quad(lbx, lby, lbw, lbh, (0.22, 0.22, 0.25), 0.95)
            ui.outline(lbx, lby, lbw, lbh, (0.5, 0.4, 0.4))
            for item in level["items"]:
                item.draw(ui, self._win_h)

    # ---- Mouse handling ----

    def on_mouse_press(self, screen_x, screen_y, button):
        if not self.visible:
            return False

        bu_y = self._flip(screen_y)  # top-down → bottom-up

        # Clear hovered state across all items
        self._clear_hover()

        # Sub-levels (deepest first)
        while self._sub_levels:
            level = self._sub_levels[-1]
            lx, ly, lw, lh = self._bounds(level["items"])
            if lx <= screen_x <= lx + lw and ly <= bu_y <= ly + lh:
                if button == 1:
                    for item in reversed(level["items"]):
                        if item.hit_test(screen_x, bu_y):
                            item.pressed = True
                            item.hovered = True
                            self._captured = item
                            if item.is_branch:
                                self._push_sub_level(item)
                            return True
                return True
            self._sub_levels.pop()

        # Top level
        bx, by, bw, bh = self._bounds(self._top_items)
        if bx <= screen_x <= bx + bw and by <= bu_y <= by + bh:
            for item in reversed(self._top_items):
                if item.hit_test(screen_x, bu_y):
                    item.pressed = True
                    item.hovered = True
                    self._captured = item
                    if item.is_branch:
                        self._push_sub_level(item)
                    return True
            self.close()
            return True
        self.close()
        return True

    def on_mouse_release(self, screen_x, screen_y, button):
        captured = self._captured
        if not captured:
            return
        captured.pressed = False
        self._captured = None
        if button == 1:
            bu_y = self._flip(screen_y)
            if (
                captured.hit_test(screen_x, bu_y)
                and not captured.is_branch
            ):
                action = captured.action
                if callable(action):
                    try:
                        action()
                    finally:
                        self.close()

    def on_mouse_move(self, screen_x, screen_y):
        if not self.visible:
            return
        bu_y = self._flip(screen_y)
        self._clear_hover()

        # Sub-levels deepest first
        for level in reversed(self._sub_levels):
            for item in reversed(level["items"]):
                if item.hit_test(screen_x, bu_y):
                    item.hovered = True
                    return

        # Top level
        for item in reversed(self._top_items):
            if item.hit_test(screen_x, bu_y):
                item.hovered = True
                return

    def _push_sub_level(self, branch):
        items = branch.sub_items
        if not items:
            return

        ox = branch.x + branch.w + 5
        oy = branch.y

        # Bounds of child items
        pad = self.PAD
        min_x = min(e.x for e in items)
        min_y = min(e.y for e in items)
        max_x = max(e.x + e.w for e in items)
        max_y = max(e.y + e.h for e in items)
        sw = max_x - min_x + pad * 2
        sh = max_y - min_y + pad * 2

        # Maintain consistent direction: all sub-levels go the same way
        if self._sub_direction is None:
            # First sub-level: prefer right, fall back to left
            if ox + sw > self._win_w:
                ox = branch.x - sw - 5
                self._sub_direction = "left" if ox >= 0 else "right"
            else:
                self._sub_direction = "right"
        elif self._sub_direction == "right":
            if ox + sw > self._win_w:
                ox = branch.x - sw - 5
                self._sub_direction = "left"
        else:  # left
            ox = branch.x - sw - 5
            if ox < 0:
                ox = branch.x + branch.w + 5
                self._sub_direction = "right"

        if oy + sh > self._win_h:
            oy = self._win_h - sh
        if oy < 0:
            oy = 0

        dx = ox + pad - min_x
        dy = oy + pad - min_y
        for e in items:
            e.x += dx
            e.y += dy

        self._sub_levels = [l for l in self._sub_levels if l.get("parent") is not branch]
        self._sub_levels.append({"items": items, "parent": branch})
