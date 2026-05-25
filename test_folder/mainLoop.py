from moderngl_window import create_window_config_instance, run_window_config_instance
import numpy as np

from settings_gui.guiRenderer import GuiRenderer
from window.mainWindow import SimulationRoom
from tile_management.tile import TileManager, Tile


class MainLoopHandler:
    def __init__(self) -> None:
        self._mouseX = 0.0
        self._mouseY = 0.0
        self._ctrl_pressed = False
        self.dashboardInstance = None
        self.guiRenderer = None

    def attach_simulation(self, simulation: object):
        if not callable(getattr(simulation, "run", None)):
            NotImplementedError("Simulation class has no callable run class")

        if callable(getattr(simulation, "attach", None)):
            print("Warning: Simualtion has not Signals")

        self._simulation = simulation

    def run(self):
        self.dashboardInstance = create_window_config_instance(SimulationRoom)
        wnd = self.dashboardInstance.wnd
        self.tileManager = TileManager(self.dashboardInstance)
        self.guiRenderer = GuiRenderer(self.dashboardInstance)

        # MainWindow Callables
        def on_mouse(x, y, dx, dy):
            self._mouseX, self._mouseY = x, y

        def on_key_press(ctrl_pressed):
            self._ctrl_pressed = ctrl_pressed

        def on_scroll(x_offset, y_offset):
            # Scroll event for widgets
            print("Callback success")

        def on_tick(time, frame_time):
            print(f"mouse={self._mouseX},{self._mouseY} ctrl={self._ctrl_pressed}")
            if self._ctrl_pressed:
                tile_n = self.tileManager.get_tile_index(self._mouseX, self._mouseY)
                self.tileManager.hovered_index = tile_n
                print(f"Tile idx: {tile_n}")

        # MainWindow Callables Attached
        self.dashboardInstance.callbacks.on_mouse = on_mouse
        self.dashboardInstance.callbacks.on_key_press = on_key_press
        self.dashboardInstance.callbacks.on_tick = on_tick
        self.dashboardInstance.callbacks.on_scroll = on_scroll

        self._render_callbacks()

        run_window_config_instance(self.dashboardInstance)

    def _render_callbacks(self):
        """
        A callback method for handling all the rendering of the widgets from the main context.
        This can be broken up into individual functions if the args expand
        """

        def render_tileManager():
            if self._ctrl_pressed:
                self.tileManager.render()

        self.dashboardInstance.callbacks.render_tileManager = render_tileManager


if __name__ == "__main__":
    main = MainLoopHandler()
    main.run()
