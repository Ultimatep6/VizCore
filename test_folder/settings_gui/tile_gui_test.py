import sys
import os
import numpy as np
import moderngl
import moderngl_window as mglw

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from settings_gui.guiManager import GuiManager
from tile_management.tile import TileManager
from tile_management import settings as tile_settings

SHADER_DIR = os.path.join(os.path.dirname(__file__), "shaders")


class TileGuiTest(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (1024, 768)
    title = "Tile GUI Test [RMB=settings  V/H=split  D=debug]"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        pw = self.wnd._window
        pw.set_fullscreen(True)
        pw.set_mouse_visible(True)

        w, h = self.wnd.size

        self._init_tiles(w, h)

        self.gui_mgr = GuiManager(self)

        with open(os.path.join(SHADER_DIR, "tile_bg.vert")) as f:
            bg_vert = f.read()
        with open(os.path.join(SHADER_DIR, "tile_bg.frag")) as f:
            bg_frag = f.read()
        self.bg_prog = self.ctx.program(vertex_shader=bg_vert, fragment_shader=bg_frag)
        self.bg_vao = self.ctx.vertex_array(self.bg_prog, [])

        self.dragging_border = False
        self.ctrl_pressed = False

    def _init_tiles(self, w, h):
        self._win_w, self._win_h = w, h
        self.tile_manager = TileManager(self, shader_dir=SHADER_DIR)
        self.tile_manager.hovered_index = 0
        self.tile_manager.set_focus(0)

    def _draw_tile_bg(self, x, y, w, h, color):
        self.bg_prog["u_resolution"] = (self._win_w, self._win_h)
        self.bg_prog["u_rect"] = (x, y, w, h)
        self.bg_prog["u_color"] = color
        self.bg_vao.render(moderngl.TRIANGLES, 6)

    def on_render(self, time, frame_time):
        self.ctx.clear(0.05, 0.05, 0.08, 1.0)
        self.ctx.disable(moderngl.DEPTH_TEST)

        for i, tile in enumerate(self.tile_manager.tiles):
            if tile.widget is not None:
                self._draw_tile_bg(
                    tile.x, tile.y, tile.width, tile.height, (0.1, 0.35, 0.1)
                )
            elif i == self.tile_manager.focus_index:
                self._draw_tile_bg(
                    tile.x, tile.y, tile.width, tile.height, (0.12, 0.14, 0.18)
                )
            else:
                self._draw_tile_bg(
                    tile.x, tile.y, tile.width, tile.height, (0.08, 0.08, 0.1)
                )

        self.tile_manager.render()

        if self.gui_mgr.show_debug:
            for tile in self.tile_manager.tiles:
                self._draw_tile_bg(
                    tile.x, tile.y, tile.width, tile.height, (0.0, 0.0, 0.0)
                )

        self.gui_mgr.render()

    def on_mouse_press_event(self, x, y, button):
        if self.gui_mgr.on_mouse_press(x, y, button):
            return

        if button == 1:
            border = self.tile_manager.get_border_at(x, y, threshold=5)
            if border:
                self.dragging_border = True
                return

            idx = self.tile_manager.get_tile_index(x, y)
            if idx is not None:
                self.tile_manager.set_focus(idx)

        elif button == 2:
            idx = self.tile_manager.get_tile_index(x, y)
            if idx is not None:
                self.tile_manager.set_focus(idx)
                tile = self.tile_manager.tiles[idx]
                self.gui_mgr.show_popup(x, y, tile=tile)

    def on_mouse_release_event(self, x, y, button):
        self.gui_mgr.on_mouse_release(x, y, button)
        if button == 1:
            self.dragging_border = False

    def on_mouse_drag_event(self, x, y, dx, dy):
        if self.dragging_border:
            self.tile_manager.resize_border(x - dx, y - dy, dx, dy, threshold=15)
        else:
            self.gui_mgr.on_mouse_drag(x, y, dx, dy)

    def on_mouse_position_event(self, x, y, dx, dy):
        self.gui_mgr.on_mouse_move(x, y, dx, dy)
        if not self.gui_mgr.popup_visible:
            idx = self.tile_manager.get_tile_index(x, y)
            self.tile_manager.hovered_index = idx

    def on_key_event(self, key, action, modifiers):
        if action == self.wnd.keys.ACTION_PRESS:
            if key == self.wnd.keys.LEFT_CTRL:
                self.ctrl_pressed = True
        elif action == self.wnd.keys.ACTION_RELEASE:
            if key == self.wnd.keys.LEFT_CTRL:
                self.ctrl_pressed = False

        if action != self.wnd.keys.ACTION_PRESS:
            return

        if key == self.wnd.keys.ESCAPE:
            self.gui_mgr.close_popup()
        elif key == self.wnd.keys.D:
            self.gui_mgr.show_debug = not self.gui_mgr.show_debug
        elif key == self.wnd.keys.S and self.gui_mgr.popup_visible:
            self.gui_mgr.print_sizing()
        elif key == self.wnd.keys.V and not self.ctrl_pressed:
            if self.tile_manager.focus_index is not None:
                self.tile_manager.split_focused_tile("vertical")
        elif key == self.wnd.keys.H and not self.ctrl_pressed:
            if self.tile_manager.focus_index is not None:
                self.tile_manager.split_focused_tile("horizontal")

    def on_resize(self, width, height):
        self.ctx.viewport = (0, 0, width, height)
        self.gui_mgr.on_resize(width, height)
        self._init_tiles(width, height)


if __name__ == "__main__":
    TileGuiTest.run()
