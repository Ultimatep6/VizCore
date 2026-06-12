import os
import numpy as np
import moderngl
import pyglet

from settings_gui.guiElement import GUIElement
from settings_gui.elements import Button, Toggle, Slider, Branch

UIElement = GUIElement  # backward compat alias

SHADER_DIR = os.path.join(os.path.dirname(__file__), "shaders")


class GuiRenderer:
    def __init__(self, ctx, width, height):
        self.ctx = ctx
        self.width = width
        self.height = height

        with open(os.path.join(SHADER_DIR, "ui.vert")) as f:
            vert_src = f.read()
        with open(os.path.join(SHADER_DIR, "ui.frag")) as f:
            frag_src = f.read()

        self.program = ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

        quad_verts = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 1.0, 1.0, 1.0], dtype="f4")
        self.quad_vbo = ctx.buffer(quad_verts.tobytes())
        self.quad_vao = ctx.vertex_array(self.program, [(self.quad_vbo, "2f", "in_vert")])

        outline_verts = np.array([0.0, 0.0, 1.0, 0.0, 1.0, 1.0, 0.0, 1.0], dtype="f4")
        self.outline_vbo = ctx.buffer(outline_verts.tobytes())
        self.outline_vao = ctx.vertex_array(self.program, [(self.outline_vbo, "2f", "in_vert")])

    def quad(self, x, y, w, h, color, alpha=1.0):
        r, g, b = color[:3]
        self.program["u_resolution"] = (self.width, self.height)
        self.program["u_pos"] = (x, y)
        self.program["u_size"] = (w, h)
        self.program["u_color"] = (r, g, b, alpha)
        if alpha < 1.0:
            self.ctx.enable(moderngl.BLEND)
        self.quad_vao.render(moderngl.TRIANGLE_STRIP)
        if alpha < 1.0:
            self.ctx.disable(moderngl.BLEND)

    def outline(self, x, y, w, h, color, alpha=1.0):
        r, g, b = color[:3]
        self.program["u_resolution"] = (self.width, self.height)
        self.program["u_pos"] = (x, y)
        self.program["u_size"] = (w, h)
        self.program["u_color"] = (r, g, b, alpha)
        self.outline_vao.render(moderngl.LINE_LOOP)

    def text(self, text_str, x, y, color=(1.0, 1.0, 1.0), scale=0.5,
             anchor_x="left", anchor_y="bottom", clip_rect=None):
        r, g, b = color[:3]
        ir, ig, ib, ia = int(r * 255), int(g * 255), int(b * 255), 255
        lbl = pyglet.text.Label(
            text_str, color=(ir, ig, ib, ia),
            anchor_x=anchor_x, anchor_y=anchor_y,
            font_size=int(10 * scale / 0.5),
            x=int(x), y=int(y),
        )
        lbl.draw()


class GuiPlayground(pyglet.window.Window):
    WINDOW_W = 480
    WINDOW_H = 540

    def __init__(self):
        super().__init__(
            self.WINDOW_W, self.WINDOW_H, "GUI Playground", resizable=False
        )
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.gui = GuiRenderer(self.ctx, self.WINDOW_W, self.WINDOW_H)
        self.elements = []
        self._hovered = None
        self._captured = None
        self._build_layout()

        self._fps = 0.0
        self._fps_frames = 0
        self._fps_timer = 0.0
        self.show_debug = True

        self._sub_levels = []
        self._sub_direction = None

        pyglet.clock.schedule_interval(self._update, 1 / 60.0)

    def _add(self, elem):
        self.elements.append(elem)
        return elem

    def _row(self, i):
        return self.WINDOW_H - 60 - i * 60

    def _build_layout(self):
        self._add(
            Button(
                20,
                self._row(0),
                440,
                36,
                "Add Slider",
                on_click=self._add_slider,
                press_color=(0.15, 0.4, 0.15),
            )
        )

        self._add(
            Toggle(
                20,
                self._row(1),
                440,
                36,
                label="Enable logging",
                initial=True,
                on_toggle=lambda v: setattr(self, "_logging", v),
            )
        )
        self._logging = True

        self._add(
            Slider(
                20,
                self._row(2),
                440,
                44,
                label="Volume",
                min_val=0,
                max_val=100,
                initial=75,
                on_change=lambda v: setattr(self, "_volume", v),
            )
        )
        self._volume = 75.0

        self._add(
            Slider(
                20,
                self._row(3),
                440,
                44,
                label="Sensitivity",
                min_val=0.1,
                max_val=10.0,
                initial=2.5,
                on_change=lambda v: setattr(self, "_sensitivity", v),
            )
        )
        self._sensitivity = 2.5

        self._add(
            Branch(
                20,
                self._row(4),
                440,
                36,
                "Sub Menu",
                sub_factory=self._build_sub_widgets,
            )
        )

        self._add(
            Button(
                20,
                self._row(5),
                440,
                36,
                "Reset Defaults",
                on_click=self._reset_defaults,
            )
        )

        self._slider_slot = self._row(6)

    def _add_slider(self):
        idx = len(self.elements)
        self._add(
            Slider(
                20,
                self._slider_slot,
                440,
                44,
                label=f"Channel {idx}",
                min_val=-1,
                max_val=1,
                initial=0,
                on_change=lambda v, i=idx: setattr(self, f"_ch{i}", v),
            )
        )
        setattr(self, f"_ch{idx}", 0.0)
        self._slider_slot -= 60
        if self._slider_slot < 60:
            self._slider_slot = self._row(5)

    def _reset_defaults(self):
        for e in self.elements:
            if isinstance(e, Toggle):
                e.state = False
            elif isinstance(e, Slider):
                e.value = (e.min_val + e.max_val) / 2
        self._logging = False
        self._volume = 50.0
        self._sensitivity = 1.0

    def _build_sub_widgets(self, ox, oy):
        return [
            Branch(
                ox + 10, oy - 35, 140, 28, "Nested", sub_factory=self._build_sub_widgets
            ),
            Toggle(ox + 10, oy - 70, 140, 28, "Option A"),
            Slider(ox + 10, oy - 115, 140, 36, "Sub Val", 0, 10, 5),
        ]

    def _level_bounds(self, elements):
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
            if ox + sw > self.WINDOW_W:
                ox = branch.x - sw - 5
                self._sub_direction = "left" if ox >= 0 else "right"
            else:
                self._sub_direction = "right"
        elif self._sub_direction == "right":
            if ox + sw > self.WINDOW_W:
                ox = branch.x - sw - 5
                self._sub_direction = "left"
        else:  # left
            ox = branch.x - sw - 5
            if ox < 0:
                ox = branch.x + branch.w + 5
                self._sub_direction = "right"

        if oy + sh > self.WINDOW_H:
            oy = self.WINDOW_H - sh
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

    def _update(self, dt):
        self._fps_frames += 1
        self._fps_timer += dt
        if self._fps_timer >= 1.0:
            self._fps = self._fps_frames / self._fps_timer
            self._fps_frames = 0
            self._fps_timer = 0.0

    def on_draw(self):
        self.ctx.clear(0.08, 0.08, 0.1, 1.0)
        self.ctx.disable(moderngl.DEPTH_TEST)

        self.gui.text(
            f"GUI Playground    FPS: {self._fps:.0f}",
            15, self.WINDOW_H - 25,
            color=(0.7, 0.7, 0.78), scale=0.6,
            anchor_x="left", anchor_y="top",
        )

        for e in self.elements:
            if e.visible:
                e.draw(self.gui)

        for level in self._sub_levels:
            sbx, sby, sbw, sbh = self._level_bounds(level["elements"])
            self.gui.quad(sbx, sby, sbw, sbh, (0.25, 0.2, 0.2))
            self.gui.outline(sbx, sby, sbw, sbh, (0.5, 0.4, 0.4))
            for e in level["elements"]:
                if e.visible:
                    e.draw(self.gui)

        if self.show_debug:
            for e in self.elements:
                if e.visible:
                    self.gui.outline(e.x, e.y, e.w, e.h, (0.0, 1.0, 1.0))
            for level in self._sub_levels:
                for e in level["elements"]:
                    if e.visible:
                        self.gui.outline(e.x, e.y, e.w, e.h, (0.0, 1.0, 1.0))
            self.gui.text(
                "Debug: ON  [D to toggle]",
                self.WINDOW_W - 160, 8,
                color=(0.0, 1.0, 1.0), scale=0.45,
                anchor_x="left", anchor_y="bottom",
            )

    def _top_element(self, x, y):
        for e in reversed(self.elements):
            if e.visible and e.hit_test(x, y):
                return e
        return None

    def on_mouse_motion(self, x, y, dx, dy):
        for e in self.elements:
            e.hovered = False
        for level in self._sub_levels:
            for e in level["elements"]:
                e.hovered = False
        for level in reversed(self._sub_levels):
            for e in reversed(level["elements"]):
                if e.visible and e.hit_test(x, y):
                    e.hovered = True
                    self._hovered = e
                    return
        self._hovered = self._top_element(x, y)
        if self._hovered:
            self._hovered.hovered = True

    def on_mouse_press(self, x, y, button, modifiers):
        while self._sub_levels:
            level = self._sub_levels[-1]
            lx, ly, lw, lh = self._level_bounds(level["elements"])
            if lx <= x <= lx + lw and ly <= y <= ly + lh:
                if button == 1:
                    for e in reversed(level["elements"]):
                        if e.hit_test_grip(x, y):
                            e.start_resize(x)
                            self._captured = e
                            return
                    for e in reversed(level["elements"]):
                        if e.hit_test(x, y):
                            e.on_mouse_press(x, y, button)
                            self._captured = e
                            if isinstance(e, Branch):
                                if (
                                    self._sub_levels
                                    and self._sub_levels[-1]["branch"] is e
                                ):
                                    self._pop_top_level()
                                else:
                                    self._push_sub_level(e)
                            return
                return
            self._pop_top_level()

        self._captured = self._top_element(x, y)
        if self._captured:
            self._captured.on_mouse_press(x, y, button)
            if isinstance(self._captured, Branch):
                if (
                    self._sub_levels
                    and self._sub_levels[-1]["branch"] is self._captured
                ):
                    self._pop_top_level()
                else:
                    self._push_sub_level(self._captured)

    def on_mouse_release(self, x, y, button, modifiers):
        if self._captured:
            was_resizing = self._captured._resizing
            self._captured.end_resize()
            if not was_resizing:
                self._captured.on_mouse_release(x, y, button)
            self._captured = None

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self._captured:
            if self._captured._resizing:
                self._captured.do_resize(x)
            else:
                self._captured.on_mouse_drag(x, y, dx, dy, buttons)

    def on_key_press(self, symbol, modifiers):
        if symbol == pyglet.window.key.D:
            self.show_debug = not self.show_debug


if __name__ == "__main__":
    GuiPlayground()
    pyglet.app.run()
