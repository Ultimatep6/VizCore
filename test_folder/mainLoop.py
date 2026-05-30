from moderngl_window import create_window_config_instance, run_window_config_instance
import moderngl
import numpy as np

from settings_gui.guiManager import GuiManager
from window.mainWindow import SimulationRoom
from tile_management.tile import TileManager, Tile


class MainLoopHandler:
    def __init__(self, fullscreen: bool = True) -> None:
        self._mouseX = 0.0
        self._mouseY = 0.0
        self._ctrl_pressed = False
        self.dashboardInstance = None
        self.guiManager = None
        self._fullscreen = fullscreen
        self._dragging_border = False

    def attach_simulation(self, simulation: object):
        if not callable(getattr(simulation, "run", None)):
            NotImplementedError("Simulation class has no callable run class")

        if callable(getattr(simulation, "attach", None)):
            print("Warning: Simualtion has not Signals")

        self._simulation = simulation

    def run(self):
        self.dashboardInstance = create_window_config_instance(SimulationRoom)
        wnd = self.dashboardInstance.wnd
        wnd._window.set_fullscreen(self._fullscreen)
        self.tileManager = TileManager(self.dashboardInstance)
        self.guiManager = GuiManager(self.dashboardInstance)

        def on_mouse(x, y, dx, dy):
            self._mouseX, self._mouseY = x, y
            self.guiManager.on_mouse_move(x, y, dx, dy)
            if not self.guiManager.popup_visible:
                idx = self.tileManager.get_tile_index(x, y)
                self.tileManager.hovered_index = idx

        def on_key_press(ctrl_pressed):
            self._ctrl_pressed = ctrl_pressed

        def on_scroll(x_offset, y_offset):
            print("Callback success")

        def on_tick(time, frame_time):
            pass

        def on_mouse_press(x, y, button):
            if self.guiManager.on_mouse_press(x, y, button):
                return
            if button == 1:
                border = self.tileManager.get_border_at(x, y, threshold=5)
                if border:
                    self._dragging_border = True
                    return
                idx = self.tileManager.get_tile_index(x, y)
                if idx is not None:
                    self.tileManager.set_focus(idx)
            elif button == 2:
                idx = self.tileManager.get_tile_index(x, y)
                if idx is not None:
                    self.tileManager.set_focus(idx)
                    tile = self.tileManager.tiles[idx]
                    self.guiManager.show_popup(x, y, tile=tile)

        def on_mouse_release(x, y, button):
            self.guiManager.on_mouse_release(x, y, button)
            if button == 1:
                self._dragging_border = False

        def on_mouse_drag(x, y, dx, dy):
            if self._dragging_border:
                self.tileManager.resize_border(x - dx, y - dy, dx, dy, threshold=15)
            else:
                self.guiManager.on_mouse_drag(x, y, dx, dy)

        def on_key_event(key, action, modifiers):
            if action != wnd.keys.ACTION_PRESS:
                return
            if key == wnd.keys.ESCAPE:
                self.guiManager.close_popup()
            elif key == wnd.keys.S and self.guiManager.popup_visible:
                self.guiManager.print_sizing()
            elif key == wnd.keys.V and not self._ctrl_pressed:
                if self.tileManager.focus_index is not None:
                    self.tileManager.split_focused_tile("vertical")
            elif key == wnd.keys.H and not self._ctrl_pressed:
                if self.tileManager.focus_index is not None:
                    self.tileManager.split_focused_tile("horizontal")

        def on_resize(width, height):
            self.guiManager.on_resize(width, height)
            self.tileManager = TileManager(self.dashboardInstance)

        def render_tileManager():
            if not self._ctrl_pressed:
                return
            ctx = self.dashboardInstance.ctx
            ctx.disable(moderngl.DEPTH_TEST)
            self.tileManager.render()
            ctx.enable(moderngl.DEPTH_TEST)

        def render_guiManager():
            if not self._ctrl_pressed:
                return
            ctx = self.dashboardInstance.ctx
            ctx.disable(moderngl.DEPTH_TEST)
            self.guiManager.render()
            ctx.enable(moderngl.DEPTH_TEST)

        self.dashboardInstance.callbacks.on_mouse = on_mouse
        self.dashboardInstance.callbacks.on_key_press = on_key_press
        self.dashboardInstance.callbacks.on_tick = on_tick
        self.dashboardInstance.callbacks.on_scroll = on_scroll
        self.dashboardInstance.callbacks.on_mouse_press = on_mouse_press
        self.dashboardInstance.callbacks.on_mouse_release = on_mouse_release
        self.dashboardInstance.callbacks.on_mouse_drag = on_mouse_drag
        self.dashboardInstance.callbacks.on_key_event = on_key_event
        self.dashboardInstance.callbacks.on_resize = on_resize

        self.dashboardInstance.render_callbacks.render_tileManager = render_tileManager
        self.dashboardInstance.render_callbacks.render_guiManager = render_guiManager

        run_window_config_instance(self.dashboardInstance)


if __name__ == "__main__":
    main = MainLoopHandler(fullscreen=True)
    main.run()
