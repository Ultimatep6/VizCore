import os
import numpy as np
import moderngl
from collections import defaultdict
import tkinter as tk
from tkinter import filedialog
from moderngl_window import create_window_config_instance, run_window_config_instance

from settings_gui.guiManager import GuiManager
from settings_gui.blipGui import BlipGui
from core.simulation import SimContainer
from window.mainWindow import SimulationRoom
from tile_management.tile import TileManager
from input_state import InputState
from window.blip import Blips
from window.model_aligner import ModelAligner
from mesh_loader import load_model
from render_pipeline import render_tiles, render_gui


class MainLoopHandler:
    def __init__(self, fullscreen: bool = True) -> None:
        self.input = InputState()
        self.dashboardInstance = None
        self.guiManager = None
        self.tileManager = None
        self._simulation = None
        self._blip_node_names = []
        self._model_repo = {}
        self._blip_models = {}
        self._next_version_counter = defaultdict(int)
        self._current_blip_idx = None
        self._paused = False
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
        self.blip_gui = BlipGui(self.dashboardInstance,
                               on_load_new=self._on_blip_new_model,
                               on_load_version=self._on_blip_load_version,
                               on_remove_model=self._on_blip_remove_model,
                               on_edit_model=self._on_blip_edit_model)
        self.blips = Blips(self.dashboardInstance)
        self.model_aligner = ModelAligner(self.dashboardInstance)
        self.model_aligner._on_done_cb = self._on_alignment_done
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
        self.blip_gui.on_mouse_move(x, y, dx, dy)
        if not self.guiManager.popup_visible:
            idx = self.tileManager.get_tile_index(x, y)
            self.tileManager.hovered_index = idx

    def _on_key_press(self, ctrl_pressed):
        self.input.ctrl_pressed = ctrl_pressed

    def _on_tick(self, time, frame_time):
        if self.model_aligner.active or self._paused:
            return
        if self._simulation is not None and callable(
            getattr(self._simulation, "step", None)
        ):
            self._simulation.step(frame_time)

    def _on_mouse_press(self, x, y, button):
        if self.model_aligner.active:
            self.model_aligner.on_mouse_press(x, y, button)
            return
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
                    self._current_blip_idx = hit_idx
                    name = self._blip_node_names[hit_idx]
                    has_model = hit_idx in self._blip_models
                    repo_entries = [
                        (v["display_name"], k)
                        for k, v in self._model_repo.items()
                    ]
                    self.blip_gui.show(x, y, name,
                                       has_model=has_model,
                                       repo_entries=repo_entries)

    def _on_mouse_release(self, x, y, button):
        if self.model_aligner.active:
            self.model_aligner.on_mouse_release(x, y, button)
            return
        self.guiManager.on_mouse_release(x, y, button)
        self.blip_gui.on_mouse_release(x, y, button)
        if button == 1:
            self.input.dragging_border = False

    def _on_scroll(self, x_offset, y_offset):
        pass

    def _on_mouse_drag(self, x, y, dx, dy):
        if self.model_aligner.active:
            self.model_aligner.on_mouse_drag(x, y, dx, dy)
            return
        if self.input.dragging_border:
            self.tileManager.resize_border(x - dx, y - dy, dx, dy, threshold=15)
        else:
            self.guiManager.on_mouse_drag(x, y, dx, dy)

    def _on_key_event(self, key, action, modifiers):
        wnd = self.dashboardInstance.wnd
        if action != wnd.keys.ACTION_PRESS:
            return
        if key == wnd.keys.ESCAPE:
            if self.model_aligner.active:
                self.model_aligner.close()
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
        elif key == wnd.keys.SPACE:
            if not self.model_aligner.active:
                self._paused = not self._paused

    def _render_tiles(self):
        if not self.input.ctrl_pressed:
            return
        render_tiles(self.dashboardInstance.ctx, self.tileManager)

    def _render_gui(self):
        if self.model_aligner.active:
            w = self.dashboardInstance.wnd.width
            h = self.dashboardInstance.wnd.height
            self.model_aligner.render(w, h)
            return
        if self.input.ctrl_pressed:
            render_gui(self.dashboardInstance.ctx, self.guiManager)
        self.blip_gui.render()

    def _on_resize(self, width, height):
        self.guiManager.on_resize(width, height)
        self.blip_gui.on_resize(width, height)
        self.model_aligner.on_resize(width, height)
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
            pos_arr = np.array(positions, dtype=np.float32)
            self.blips.set_positions(pos_arr)
            for blip_idx in self._blip_models:
                if blip_idx < len(positions):
                    self.blips.set_active(blip_idx, False)
        self._blip_node_names = names
        self.blips.render(vp, camera_pos)

        # Render models for assigned blips
        if self._blip_models and positions:
            prog = self.model_aligner.model_program
            for blip_idx, version_id in list(self._blip_models.items()):
                if blip_idx >= len(positions):
                    continue
                entry = self._model_repo.get(version_id)
                if entry is None:
                    continue
                pos = positions[blip_idx]
                prog["u_vp"].write(vp.astype("f4").T.tobytes())
                prog["u_offset"].write(np.array(pos, dtype="f4").tobytes())
                prog["u_rotation"].write(np.eye(3, dtype="f4").tobytes())
                prog["u_scale"].write(np.float32(1.0))
                prog["u_color"].write(
                    np.array([0.3, 0.8, 0.9], dtype="f4").tobytes()
                )
                entry["vao"].render(moderngl.TRIANGLES, entry["n_indices"])

    def _pick_obj_file(self):
        root = tk.Tk()
        root.withdraw()
        path = filedialog.askopenfilename(
            title="Select .obj model",
            filetypes=[("OBJ files", "*.obj"), ("All files", "*.*")]
        )
        root.destroy()
        return path

    def _on_blip_new_model(self):
        path = self._pick_obj_file()
        if not path:
            return
        data = load_model(path)
        verts = data["vertices"].astype(np.float32)
        normals = data["normals"].astype(np.float32)
        indices = data["indices"]
        if len(indices) == 0 or len(verts) == 0:
            print("No vertices or indices in model")
            return
        stem = os.path.splitext(os.path.basename(path))[0]
        self._next_version_counter[stem] += 1
        version_id = f"{stem}_V{self._next_version_counter[stem]}"

        # Normalize model so bounding box fits in unit sphere
        c = (verts.min(axis=0) + verts.max(axis=0)) / 2
        r = np.max(verts.max(axis=0) - verts.min(axis=0)) / 2
        if r > 1e-8:
            verts = (verts - c) / r

        flat_indices = np.ascontiguousarray(indices.ravel().astype(np.int32))
        n_indices = len(flat_indices)
        ctx = self.dashboardInstance.ctx
        vbo_verts = ctx.buffer(verts.tobytes())
        vbo_normals = ctx.buffer(normals.tobytes())
        ibo = ctx.buffer(flat_indices.tobytes())
        prog = self.model_aligner.model_program
        vao = ctx.vertex_array(
            prog,
            [(vbo_verts, "3f", "in_vert"), (vbo_normals, "3f", "in_normal")],
            ibo,
        )
        self._model_repo[version_id] = {
            "verts": verts,
            "normals": normals,
            "indices": indices,
            "aligned_verts": verts.copy(),
            "aligned_normals": normals.copy(),
            "vbo_verts": vbo_verts,
            "vbo_normals": vbo_normals,
            "vao": vao,
            "n_indices": n_indices,
            "display_name": version_id,
        }
        self.model_aligner.load_model(version_id, verts, normals, indices)
        self.model_aligner.show()

    def _on_blip_load_version(self, version_id):
        if version_id in self._model_repo and self._current_blip_idx is not None:
            self._blip_models[self._current_blip_idx] = version_id

    def _on_blip_remove_model(self):
        if self._current_blip_idx is not None and self._current_blip_idx in self._blip_models:
            del self._blip_models[self._current_blip_idx]
            self.blips.set_active(self._current_blip_idx, True)

    def _on_blip_edit_model(self):
        if self._current_blip_idx is None:
            return
        version_id = self._blip_models.get(self._current_blip_idx)
        if version_id is None:
            return
        entry = self._model_repo.get(version_id)
        if entry is None:
            return
        self.model_aligner.load_model(
            version_id, entry["verts"], entry["normals"], entry["indices"]
        )
        self.model_aligner.show()

    def _on_alignment_done(self, version_id, aligned_verts, aligned_normals):
        entry = self._model_repo.get(version_id)
        if entry is None:
            return
        entry["vbo_verts"].write(aligned_verts.astype(np.float32).tobytes())
        entry["vbo_normals"].write(aligned_normals.astype(np.float32).tobytes())
        entry["aligned_verts"] = aligned_verts
        entry["aligned_normals"] = aligned_normals
        if self._current_blip_idx is not None:
            self._blip_models[self._current_blip_idx] = version_id


if __name__ == "__main__":
    from exampleSim import ExampleSim

    main = MainLoopHandler(fullscreen=True)
    main.attach_simulation(ExampleSim())
    main.run()
