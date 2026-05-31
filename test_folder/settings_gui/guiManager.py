from guiRenderer import GuiRenderer
from elements import Button, Branch


class GuiManager:
    def __init__(self, mainWindow, widgets=None):
        self.renderer = GuiRenderer(mainWindow)
        self._widgets = widgets or ["Chart", "Plugin A", "Plugin B"]

        self._win_w = mainWindow.wnd.width
        self._win_h = mainWindow.wnd.height

        self.popup_visible = False
        self.popup_elements = []
        self.popup_x = 0
        self.popup_y = 0
        self._sub_levels = []
        self._captured = None

        self.show_debug = False
        self._popup_tile = None

    def _flip(self, y):
        return self._win_h - y

    def show_popup(self, x, y, tile=None):
        self.popup_x = x
        self.popup_y = self._flip(y)
        self.popup_visible = True
        self._sub_levels.clear()
        self._captured = None
        self._popup_tile = tile
        if tile is not None:
            self._build_tile_popup(tile)
        else:
            self.popup_elements = []

    def close_popup(self):
        self.popup_visible = False
        self.popup_elements = []
        self._sub_levels.clear()
        self._captured = None
        self._popup_tile = None

    def _build_tile_popup(self, tile):
        y_off = self.popup_y - 35
        if tile.widget is not None:
            self.popup_elements = [
                Button(
                    self.popup_x + 10,
                    y_off,
                    140,
                    28,
                    f"Remove {tile.widget}",
                    on_click=lambda t=tile: self._remove_widget(t),
                ),
            ]
        else:
            self.popup_elements = [
                Branch(
                    self.popup_x + 10,
                    y_off,
                    140,
                    28,
                    "Add Widget",
                    sub_factory=self._build_widget_list,
                ),
            ]
        self._clamp_popup()

    def _build_widget_list(self, ox, oy):
        return [
            Button(
                ox + 10,
                oy - 35 - i * 40,
                140,
                28,
                name,
                on_click=lambda n=name: self._add_widget(n),
            )
            for i, name in enumerate(self._widgets)
        ]

    def _add_widget(self, name):
        if self._popup_tile is None:
            return
        self._popup_tile.widget = name
        self._rebuild_popup()

    def _remove_widget(self, tile):
        tile.widget = None
        self._popup_tile = tile
        self._rebuild_popup()

    def _rebuild_popup(self):
        if self._popup_tile is None:
            return
        self._build_tile_popup(self._popup_tile)
        self._sub_levels.clear()

    def _popup_bounds(self):
        if not self.popup_elements:
            return (self.popup_x, self.popup_y - 140, 160, 140)
        pad = 10
        min_x = min(e.x for e in self.popup_elements) - pad
        min_y = min(e.y for e in self.popup_elements) - pad
        max_x = max(e.x + e.w for e in self.popup_elements) + pad
        max_y = max(e.y + e.h for e in self.popup_elements) + pad
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def _clamp_popup(self):
        bx, by, bw, bh = self._popup_bounds()
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
            self.popup_x += dx
            self.popup_y += dy
            for e in self.popup_elements:
                e.x += dx
                e.y += dy

    @staticmethod
    def _level_bounds(elements):
        if not elements:
            return (0, 0, 0, 0)
        pad = 10
        min_x = min(e.x for e in elements) - pad
        min_y = min(e.y for e in elements) - pad
        max_x = max(e.x + e.w for e in elements) + pad
        max_y = max(e.y + e.h for e in elements) + pad
        return (min_x, min_y, max_x - min_x, max_y - min_y)

    def _push_sub_level(self, branch):
        pad = 10
        elements = branch.sub_factory(0, 0)
        min_x = min(e.x for e in elements)
        min_y = min(e.y for e in elements)
        max_x = max(e.x + e.w for e in elements)
        max_y = max(e.y + e.h for e in elements)
        sw = max_x - min_x + pad * 2
        sh = max_y - min_y + pad * 2
        ox = branch.x + branch.w + 5
        oy = branch.y
        if ox + sw > self._win_w:
            ox = branch.x - sw - 5
        if oy + sh > self._win_h:
            oy = self._win_h - sh
        if oy < 0:
            oy = 0
        dx = ox + pad - min_x
        dy = oy + pad - min_y
        for e in elements:
            e.x += dx
            e.y += dy
        self._sub_levels.append({"elements": elements, "branch": branch})

    def _pop_top_level(self):
        if self._sub_levels:
            self._sub_levels.pop()

    def render(self):
        if not self.popup_visible:
            return
        bx, by, bw, bh = self._popup_bounds()
        self.renderer.quad(bx, by, bw, bh, (0.2, 0.2, 0.25))
        self.renderer.outline(bx, by, bw, bh, (0.4, 0.4, 0.5))
        for e in self.popup_elements:
            if e.visible:
                e.draw(self.renderer)
        for level in self._sub_levels:
            sbx, sby, sbw, sbh = self._level_bounds(level["elements"])
            self.renderer.quad(sbx, sby, sbw, sbh, (0.25, 0.2, 0.2))
            self.renderer.outline(sbx, sby, sbw, sbh, (0.5, 0.4, 0.4))
            for e in level["elements"]:
                if e.visible:
                    e.draw(self.renderer)
        if self.show_debug:
            for e in self.popup_elements:
                self.renderer.outline(e.x, e.y, e.w, e.h, (0.0, 1.0, 1.0))
            for level in self._sub_levels:
                for e in level["elements"]:
                    self.renderer.outline(e.x, e.y, e.w, e.h, (0.0, 1.0, 1.0))

    def on_mouse_press(self, x, y, button):
        if not self.popup_visible:
            return False
        fy = self._flip(y)
        while self._sub_levels:
            level = self._sub_levels[-1]
            lx, ly, lw, lh = self._level_bounds(level["elements"])
            if lx <= x <= lx + lw and ly <= fy <= ly + lh:
                if button == 1:
                    for e in reversed(level["elements"]):
                        if e.hit_test(x, fy):
                            e.on_mouse_press(x, fy, button)
                            self._captured = e
                            if isinstance(e, Branch):
                                if (
                                    self._sub_levels
                                    and self._sub_levels[-1]["branch"] is e
                                ):
                                    self._pop_top_level()
                                else:
                                    self._push_sub_level(e)
                            return True
                return True
            self._pop_top_level()
        bx, by, bw, bh = self._popup_bounds()
        if bx <= x <= bx + bw and by <= fy <= by + bh:
            for e in reversed(self.popup_elements):
                if e.hit_test(x, fy):
                    e.on_mouse_press(x, fy, button)
                    self._captured = e
                    if isinstance(e, Branch):
                        if self._sub_levels and self._sub_levels[-1]["branch"] is e:
                            self._pop_top_level()
                        else:
                            self._push_sub_level(e)
                    return True
            self.close_popup()
            return True
        self.close_popup()
        return True

    def on_mouse_release(self, x, y, button):
        if self._captured:
            self._captured.on_mouse_release(x, self._flip(y), button)
            self._captured = None

    def on_mouse_drag(self, x, y, dx, dy):
        if self._captured:
            self._captured.on_mouse_drag(x, self._flip(y), dx, dy, 1)

    def on_mouse_move(self, x, y, dx, dy):
        if not self.popup_visible:
            return
        fy = self._flip(y)
        for e in self.popup_elements:
            e.hovered = False
        for level in self._sub_levels:
            for e in level["elements"]:
                e.hovered = False
        for level in reversed(self._sub_levels):
            for e in reversed(level["elements"]):
                if e.visible and e.hit_test(x, fy):
                    e.hovered = True
                    return
        for e in reversed(self.popup_elements):
            if e.visible and e.hit_test(x, fy):
                e.hovered = True
                return

    def on_resize(self, width, height):
        self._win_w = width
        self._win_h = height
        self.renderer.width = width
        self.renderer.height = height

    def print_sizing(self):
        print("=== GUI SIZING ===")
        print(f"Window: {self._win_w}x{self._win_h}")
        if self.popup_visible:
            bx, by, bw, bh = self._popup_bounds()
            print(f"Popup background:  x={bx:4.0f} y={by:4.0f}  {bw:3.0f}x{bh:3.0f}")
            for i, e in enumerate(self.popup_elements):
                print(
                    f"  [{i}] {type(e).__name__:6s}: x={e.x:4.0f} y={e.y:4.0f}  {e.w:3.0f}x{e.h:3.0f}"
                )
            for li, level in enumerate(self._sub_levels):
                sbx, sby, sbw, sbh = self._level_bounds(level["elements"])
                print(
                    f"  Sub-level[{li}] bg: x={sbx:4.0f} y={sby:4.0f}  {sbw:3.0f}x{sbh:3.0f}"
                )
                for i, e in enumerate(level["elements"]):
                    print(
                        f"    [{i}] {type(e).__name__:6s}: x={e.x:4.0f} y={e.y:4.0f}  {e.w:3.0f}x{e.h:3.0f}"
                    )
        print("================")
