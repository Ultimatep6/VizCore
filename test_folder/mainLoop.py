import os
from moderngl_window import create_window_config_instance, run_window_config_instance
import moderngl
import numpy as np

from settings_gui.guiManager import GuiManager
from core.simulation import SimContainer
from window.mainWindow import SimulationRoom
from window import settings as window_settings
from tile_management.tile import TileManager
from input_state import InputState
from render_pipeline import (
    render_tiles,
    render_gui,
    render_nodes,
    render_indicators,
    render_cylinders,
    generate_sphere_geometry,
)


class MainLoopHandler:
    def __init__(
        self,
        fullscreen: bool = True,
        position_signal_name: str = "position",
        position_schema=None,
    ) -> None:
        self.input = InputState()
        self.dashboardInstance = None
        self.guiManager = None
        self.tileManager = None
        self._simulation = None

        self._fullscreen = fullscreen

        # Signal Stuff from Program
        self._position_signal_name = position_signal_name
        self._position_schema = position_schema
        self._position_paths = []
        self._position_values = np.empty((0, 3), dtype=np.float32)
        self._sphere_program = None
        self._sphere_vao = None
        self._sphere_instance_buf = None

    def attach_simulation(self, simulation: SimContainer):

        if not callable(getattr(simulation, "step", None)):
            NotImplementedError("Simulation class has no callable step class")

        self._simulation = simulation
        self._signal_schemas = self._simulation.get_signal_schemas()
        self._scan_default_signals(self._signal_schemas)

    def _scan_default_signals(self, schemas):
        if self._simulation is None:
            self._position_paths = []
            return
        paths = [
            path
            for path in schemas
            if path.split(".")[-1] == self._position_signal_name
        ]
        if self._position_schema is not None:
            paths = [p for p in paths if self._position_schema.matches(schemas[p])]
        self._position_paths = paths

    def _read_default_signals(self):
        if self._simulation is None or not self._position_paths:
            self._position_values = np.empty((0, 3), dtype=np.float32)
            return
        vals = []
        for path in self._position_paths:
            val = self._simulation.get_value_at(path)
            vals.append(val[:3] if hasattr(val, "__len__") else [val, 0.0, 0.0])
        self._position_values = np.array(vals, dtype=np.float32)

    def run(self):
        self.dashboardInstance = create_window_config_instance(SimulationRoom)
        wnd = self.dashboardInstance.wnd
        wnd._window.set_fullscreen(self._fullscreen)
        self.tileManager = TileManager(self.dashboardInstance)
        self.guiManager = GuiManager(self.dashboardInstance)
        self._setup_sphere()
        self._bind_callbacks()
        self._read_default_signals()
        run_window_config_instance(self.dashboardInstance)

    def _setup_sphere(self):
        ctx = self.dashboardInstance.ctx
        prog = self.dashboardInstance.load_program(
            vertex_shader=os.path.join(window_settings.SHADER_DIR, "sim_sphere.vert"),
            fragment_shader=os.path.join(window_settings.SHADER_DIR, "sim_sphere.frag"),
        )
        verts, norms, idx = generate_sphere_geometry(
            window_settings.SPHERE_RADIUS,
            window_settings.SPHERE_SECTORS,
            window_settings.SPHERE_RINGS,
        )
        vbo_vert = ctx.buffer(verts.tobytes())
        vbo_norm = ctx.buffer(norms.tobytes())
        ibo = ctx.buffer(idx.tobytes())
        instance_buf = ctx.buffer(reserve=window_settings.MAX_SPHERE_INSTANCES * 3 * 4)
        vao = ctx.vertex_array(
            prog,
            [
                (vbo_vert, "3f", "in_vert"),
                (vbo_norm, "3f", "in_normal"),
                (instance_buf, "3f/i", "in_pos"),
            ],
            ibo,
        )
        self._sphere_program = prog
        self._sphere_vao = vao
        self._sphere_instance_buf = instance_buf

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
        self._read_default_signals()

    def _on_mouse_press(self, x, y, button):
        if self.guiManager.on_mouse_press(x, y, button):
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
            idx = self.tileManager.get_tile_index(x, y)
            if idx is not None:
                self.tileManager.set_focus(idx)
                tile = self.tileManager.tiles[idx]
                self.guiManager.show_popup(x, y, tile=tile)

    def _on_mouse_release(self, x, y, button):
        self.guiManager.on_mouse_release(x, y, button)
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
        if not self.input.ctrl_pressed:
            return
        render_gui(self.dashboardInstance.ctx, self.guiManager)

    def _render_nodes(self, vp):
        instance = self.dashboardInstance
        if self._sphere_program is None:
            return
        render_nodes(
            instance.ctx,
            vp,
            self._sphere_program,
            self._sphere_vao,
            self._sphere_instance_buf,
            self._position_values,
            window_settings.SPHERE_RADIUS,
            window_settings.SPHERE_COLOR,
        )
        render_indicators(
            instance.ctx,
            vp,
            instance.indicator_program,
            instance.circle_vao,
            self._position_values,
            window_settings.INDICATOR_RADIUS,
            window_settings.INDICATOR_COLOR,
        )
        render_cylinders(
            instance.ctx,
            vp,
            instance.cylinder_program,
            instance.cylinder_vao,
            self._position_values,
            window_settings.BEAM_RADIUS,
            window_settings.SPHERE_COLOR,
            window_settings.MAX_BODIES,
        )


    def _on_resize(self, width, height):
        self.guiManager.on_resize(width, height)
        self.tileManager = TileManager(self.dashboardInstance)


if __name__ == "__main__":
    from exampleSim import ExampleSim

    main = MainLoopHandler(fullscreen=True)
    main.attach_simulation(ExampleSim())
    main.run()
