import numpy as np
from moderngl_window import create_window_config_instance, run_window_config_instance

from settings_gui.guiManager import GuiManager
from settings_gui.blipGui import BlipGui
from core.simulation import SimContainer
from window.mainWindow import SimulationRoom
from tile_management.tile import TileManager
from input_state import InputState
from window.blip import Blips
from render_pipeline import render_tiles, render_gui


class MainLoopHandler:
    def __init__(self, fullscreen: bool = True) -> None:
        self.input = InputState()
        self.dashboardInstance = None
        self.guiManager = None
        self.tileManager = None
        self._simulation = None
        self._blip_node_names = []
        self._fullscreen = fullscreen

    def attach_simulation(self, simulation: SimContainer):
        if not callable(getattr(simulation, "step", None)):
            NotImplementedError("Simulation class has no callable step class")
        self._simulation = simulation

    def run(self):
        self.dashboardInstance = create_window_config_instance(SimulationRoom)
        wnd = self.dashboardInstance.wnd
        wnd._window.set_fullscreen(self._fullscreen)
        self.tileManager = TileManager(self.dashboardInstance)
        self.guiManager = GuiManager(self.dashboardInstance)
        self.blip_gui = BlipGui(self.dashboardInstance)
        self.blips = Blips(self.dashboardInstance)
        self._bind_callbacks()
        run_window_config_instance(self.dashboardInstance)

    def _bind_callbacks(self):
        dc = self.dashboardInstance.callbacks
        dc.on_mouse = self._on_mouse
        dc.on_key_press = self._on_key_press
        dc.on_scroll = self._on_scroll
        dc.on_tick = self._on_tick
        dc.on_mouse_press = self._on_mouse_press
        dc.on_mouse_release = self._on_mouse_release
        dc.on_mouse_drag = self._on_mouse_drag
        dc.on_key_event = self._on_key_event
        dc.on_resize = self._on_resize

        rc = self.dashboardInstance.render_callbacks
        rc.render_tileManager = self._render_tiles
        rc.render_guiManager = self._render_gui
        rc.render_nodes = self._render_nodes

    def _on_mouse(self, x, y, dx, dy):
        self.input.x, self.input.y = x, y
        self.guiManager.on_mouse_move(x, y, dx, dy)
        if not self.guiManager.popup_visible:
            idx = self.tileManager.get_tile_index(x, y)
            self.tileManager.hovered_index = idx

    def _on_key_press(self, ctrl_pressed):
        self.input.ctrl_pressed = ctrl_pressed

    def _on_tick(self, time, frame_time):
        if self._simulation is not None and callable(
            getattr(self._simulation, "step", None)
        ):
            self._simulation.step(frame_time)

    def _on_mouse_press(self, x, y, button):
        if self.guiManager.on_mouse_press(x, y, button):
            return
        if self.blip_gui.on_mouse_press(x, y, button):
            return
        if button == 1:
            border = self.tileManager.get_border_at(x, y, threshold=5)
            if border:
                self.input.dragging_border = True
                return
            idx = self.tileManager.get_tile_index(x, y)
            if idx is not None:
                self.tileManager.set_focus(idx)
        elif button == 2:
            if self.input.ctrl_pressed:
                idx = self.tileManager.get_tile_index(x, y)
                if idx is not None:
                    self.tileManager.set_focus(idx)
                    tile = self.tileManager.tiles[idx]
                    self.guiManager.show_popup(x, y, tile=tile)
            else:
                if not hasattr(self, "_last_vp"):
                    return
                w = self.dashboardInstance.wnd.width
                h = self.dashboardInstance.wnd.height
                hit_idx = self.blips.pick(
                    x, y, self._last_vp, self._last_camera_pos, (w, h)
                )
                if hit_idx is not None:
                    name = self._blip_node_names[hit_idx]
                    self.blip_gui.show(x, y, name)

    def _on_mouse_release(self, x, y, button):
        self.guiManager.on_mouse_release(x, y, button)
        self.blip_gui.on_mouse_release(x, y, button)
        if button == 1:
            self.input.dragging_border = False

    def _on_scroll(self, x_offset, y_offset):
        pass

    def _on_mouse_drag(self, x, y, dx, dy):
        if self.input.dragging_border:
            self.tileManager.resize_border(x - dx, y - dy, dx, dy, threshold=15)
        else:
            self.guiManager.on_mouse_drag(x, y, dx, dy)

    def _on_key_event(self, key, action, modifiers):
        wnd = self.dashboardInstance.wnd
        if action != wnd.keys.ACTION_PRESS:
            return
        if key == wnd.keys.ESCAPE:
            self.guiManager.close_popup()
            self.blip_gui.close()
        elif key == wnd.keys.S and self.guiManager.popup_visible:
            self.guiManager.print_sizing()
        elif key == wnd.keys.V and not self.input.ctrl_pressed:
            if self.tileManager.focus_index is not None:
                self.tileManager.split_focused_tile("vertical")
        elif key == wnd.keys.H and not self.input.ctrl_pressed:
            if self.tileManager.focus_index is not None:
                self.tileManager.split_focused_tile("horizontal")

    def _render_tiles(self):
        if not self.input.ctrl_pressed:
            return
        render_tiles(self.dashboardInstance.ctx, self.tileManager)

    def _render_gui(self):
        if self.input.ctrl_pressed:
            render_gui(self.dashboardInstance.ctx, self.guiManager)
        self.blip_gui.render()

    def _on_resize(self, width, height):
        self.guiManager.on_resize(width, height)
        self.blip_gui.on_resize(width, height)
        self.tileManager = TileManager(self.dashboardInstance)

    def _render_nodes(self, vp, camera_pos):
        self._last_vp = vp
        self._last_camera_pos = camera_pos
        sim = self._simulation
        if sim is None:
            return
        schemas = sim.get_signal_schemas()
        positions = []
        names = []
        for path in schemas:
            if path.endswith(".position") or path == "position":
                val = sim.get_value_at(path)
                if val is not None:
                    positions.append(val)
                    if path == "position":
                        names.append("root")
                    else:
                        node_path = ".".join(path.split(".")[:-1])
                        try:
                            node_obj = sim.get_value_at(node_path)
                            names.append(getattr(node_obj, "name", node_path))
                        except Exception:
                            names.append(node_path)
        if positions:
            self.blips.set_positions(np.array(positions, dtype=np.float32))
        self._blip_node_names = names
        self.blips.render(vp, camera_pos)


if __name__ == "__main__":
    from exampleSim import ExampleSim

    main = MainLoopHandler(fullscreen=True)
    main.attach_simulation(ExampleSim())
    main.run()
