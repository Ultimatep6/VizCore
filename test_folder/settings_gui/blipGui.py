from settings_gui.guiRenderer import GuiRenderer
from settings_gui.elements import Button, Branch


class BlipGui:
    def __init__(self, mainWindow, on_load_new=None, on_load_version=None,
                 on_remove_model=None, on_edit_model=None):
        self.renderer = GuiRenderer(mainWindow)
        self._win_w = mainWindow.wnd.width
        self._win_h = mainWindow.wnd.height
        self.visible = False
        self._elements = []
        self._captured = None
        self._sub_levels = []
        self._sub_direction = None
        self._x = 0
        self._y = 0
        self._node_name = ""
        self._on_load_new = on_load_new
        self._on_load_version = on_load_version
        self._on_remove_model = on_remove_model
        self._on_edit_model = on_edit_model

    def show(self, x, y, node_name, has_model=False, repo_entries=None):
        self._x = x
        self._y = y
        self._node_name = node_name
        self.visible = True
        self._captured = None
        self._sub_levels.clear()
        if has_model:
            self._build_has_model(repo_entries or [])
        else:
            self._build_no_model(repo_entries or [])

    def close(self):
        self.visible = False
        self._elements = []
        self._captured = None
        self._sub_levels.clear()
        self._sub_direction = None

    def _build_no_model(self, repo_entries):
        y_off = self._y
        self._label_x = self._x + 10
        self._label_y = y_off + 30
        self._label_y_top = y_off + 30
        self._elements = [
            Button(self._x + 10, y_off, 140, 28, "Print Blip",
                   on_click=lambda n=self._node_name: print(f"Blip: {n}")),
            Branch(self._x + 10, y_off - 38, 140, 28, "Load Model",
                   sub_factory=lambda ox, oy: self._load_model_submenu(ox, oy, repo_entries)),
        ]

    def _build_has_model(self, repo_entries):
        y_off = self._y
        self._label_x = self._x + 10
        self._label_y = y_off + 30
        self._label_y_top = y_off + 30
        self._elements = [
            Button(self._x + 10, y_off, 140, 28, "Print Blip",
                   on_click=lambda n=self._node_name: print(f"Blip: {n}")),
            Button(self._x + 10, y_off - 38, 140, 28, "Edit Model",
                   on_click=self._on_edit_model),
            Button(self._x + 10, y_off - 76, 140, 28, "Remove Model",
                   on_click=self._on_remove_model),
            Branch(self._x + 10, y_off - 114, 140, 28, "Load Model",
                   sub_factory=lambda ox, oy: self._load_model_submenu(ox, oy, repo_entries)),
        ]

    def _load_model_submenu(self, ox, oy, repo_entries):
        items = [
            Button(ox + 10, oy - 35, 140, 28, "New...",
                   on_click=self._on_load_new),
        ]
        for name, vid in repo_entries:
            items.append(
                Button(ox + 10, oy - 35 - len(items) * 40, 140, 28, name,
                       on_click=lambda v=vid: self._on_load_version(v) if self._on_load_version else None)
            )
        return items

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
        self.renderer.text(self._node_name, self._label_x, self._label_y,
                           anchor_x="left", anchor_y="bottom", scale=0.6)
        for e in self._elements:
            if e.visible:
                e.draw(self.renderer)
        for level in self._sub_levels:
            sbx, sby, sbw, sbh = self._level_bounds(level["elements"])
            self.renderer.quad(sbx, sby, sbw, sbh, (0.25, 0.2, 0.2))
            self.renderer.outline(sbx, sby, sbw, sbh, (0.5, 0.4, 0.4))
            for e in level["elements"]:
                if e.visible:
                    e.draw(self.renderer)

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

        # Maintain consistent direction across nested sub-levels
        if self._sub_direction is None:
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
        for e in elements:
            e.x += dx
            e.y += dy
        self._sub_levels.append({"elements": elements, "branch": branch})

    def _pop_top_level(self):
        if self._sub_levels:
            self._sub_levels.pop()
        if not self._sub_levels:
            self._sub_direction = None

    def on_mouse_press(self, x, y, button):
        if not self.visible:
            return False
        while self._sub_levels:
            level = self._sub_levels[-1]
            lx, ly, lw, lh = self._level_bounds(level["elements"])
            if lx <= x <= lx + lw and ly <= y <= ly + lh:
                if button == 1:
                    for e in reversed(level["elements"]):
                        if e.hit_test(x, y):
                            e.hovered = True
                            e.on_mouse_press(x, y, button)
                            self._captured = e
                            if isinstance(e, Branch):
                                if (self._sub_levels
                                        and self._sub_levels[-1]["branch"] is e):
                                    self._pop_top_level()
                                else:
                                    self._push_sub_level(e)
                            return True
                return True
            self._pop_top_level()
        bx, by, bw, bh = self._bounds()
        if bx <= x <= bx + bw and by <= y <= by + bh:
            for e in reversed(self._elements):
                if e.hit_test(x, y):
                    e.hovered = True
                    e.on_mouse_press(x, y, button)
                    self._captured = e
                    if isinstance(e, Branch):
                        if (self._sub_levels
                                and self._sub_levels[-1]["branch"] is e):
                            self._pop_top_level()
                        else:
                            self._push_sub_level(e)
                    return True
            self.close()
            return True
        self.close()
        return True

    def on_mouse_release(self, x, y, button):
        if self._captured:
            self._captured.on_mouse_release(x, y, button)
            self._captured = None

    def on_mouse_move(self, x, y, dx, dy):
        if not self.visible:
            return
        for e in self._elements:
            e.hovered = False
        for level in self._sub_levels:
            for e in level["elements"]:
                e.hovered = False
        for level in reversed(self._sub_levels):
            for e in reversed(level["elements"]):
                if e.visible and e.hit_test(x, y):
                    e.hovered = True
                    return
        for e in reversed(self._elements):
            if e.visible and e.hit_test(x, y):
                e.hovered = True
                return

    def on_resize(self, width, height):
        self._win_w = width
        self._win_h = height
        self.renderer.width = width
        self.renderer.height = height
