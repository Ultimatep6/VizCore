"""Simulation room widget with dynamic bounding box and 4 corner cameras."""

import numpy as np
import moderngl
from vizcore.components.base.baseWidget import BaseWidget
from vizcore.renderer.camera import Camera
from vizcore.meshes.arrow import build_axis
import os


class SimulationRoomWidget(BaseWidget):
    """3D simulation room with dynamic bounding box and 4 corner cameras.

    Features:
    - 5-face grid (floor + 4 walls) with LOD-based detail
    - 4 cameras at upper corners, switchable with A/D keys when focused
    - Origin axis at (0,0,0) - stays fixed
    - Dynamic room bounds computed from asset positions
    - Asset cubes rendered as simple boxes
    """

    def __init__(self, initial_size=10.0, **kwargs):
        super().__init__()

        self.room_center = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.room_size = initial_size
        self.min_size = 1.0
        self.margin = 0.2

        self.cameras = []
        self.current_camera = 0

        self.assets = []

        self._grid_vao = None
        self._cube_vao = None
        self._axis_vao = None

        self._grid_vbo = None
        self._cube_vbo = None
        self._axis_vert_vbo = None
        self._axis_color_vbo = None
        self._axis_ibo = None

        self._focused = False

    @property
    def required_shape(self):
        return None

    def load_shaders(self, shader_manager):
        shader_manager.load_shader(
            "room_grid",
            vertex_path="vizcore/shaders/room_grid.vert",
            fragment_path="vizcore/shaders/room_grid.frag",
        )
        shader_manager.load_shader(
            "cube",
            vertex_path="vizcore/shaders/cube.vert",
            fragment_path="vizcore/shaders/cube.frag",
        )
        shader_manager.load_shader(
            "axis",
            vertex_path="vizcore/shaders/axis.vert",
            fragment_path="vizcore/shaders/axis.frag",
        )

    def bind_renderer(self, renderer):
        super().bind_renderer(renderer)
        self.load_shaders(renderer.shader_manager)

        self._setup_cameras()
        self._setup_grid_geometry()
        self._setup_axis_geometry()

        if os.environ.get("SIMULATION_ROOM_TEST") == "1":
            self.add_cube([0, 1, 0], [0, 1, 0], 2.0)

    def _setup_cameras(self):
        self.cameras = []
        for _ in range(4):
            camera = Camera(
                window_size=(self._tile_width, self._tile_height),
                eye=np.array([0.0, 0.0, 0.0], dtype=np.float32),
                target=np.array([0.0, 0.0, 0.0], dtype=np.float32),
                move_speed=0.0,
            )
            self.cameras.append(camera)
        self._update_camera_positions()

    def _update_camera_positions(self):
        half_size = self.room_size * 0.5
        positions = [
            np.array([-half_size, self.room_size, -half_size], dtype=np.float32),
            np.array([half_size, self.room_size, -half_size], dtype=np.float32),
            np.array([-half_size, self.room_size, half_size], dtype=np.float32),
            np.array([half_size, self.room_size, half_size], dtype=np.float32),
        ]
        for i, camera in enumerate(self.cameras):
            camera.eye = positions[i] + self.room_center

    def _setup_grid_geometry(self):
        half_size = self.room_size * 0.5

        floor = np.array(
            [
                [-half_size, 0.0, -half_size],
                [half_size, 0.0, -half_size],
                [half_size, 0.0, half_size],
                [-half_size, 0.0, -half_size],
                [half_size, 0.0, half_size],
                [-half_size, 0.0, half_size],
            ],
            dtype=np.float32,
        )

        wall_pos_x = np.array(
            [
                [half_size, 0.0, -half_size],
                [half_size, self.room_size, -half_size],
                [half_size, self.room_size, half_size],
                [half_size, 0.0, -half_size],
                [half_size, self.room_size, half_size],
                [half_size, 0.0, half_size],
            ],
            dtype=np.float32,
        )

        wall_neg_x = np.array(
            [
                [-half_size, 0.0, half_size],
                [-half_size, self.room_size, half_size],
                [-half_size, self.room_size, -half_size],
                [-half_size, 0.0, half_size],
                [-half_size, self.room_size, -half_size],
                [-half_size, 0.0, -half_size],
            ],
            dtype=np.float32,
        )

        wall_pos_z = np.array(
            [
                [-half_size, 0.0, half_size],
                [half_size, 0.0, half_size],
                [half_size, self.room_size, half_size],
                [-half_size, 0.0, half_size],
                [half_size, self.room_size, half_size],
                [-half_size, self.room_size, half_size],
            ],
            dtype=np.float32,
        )

        wall_neg_z = np.array(
            [
                [half_size, 0.0, -half_size],
                [-half_size, 0.0, -half_size],
                [-half_size, self.room_size, -half_size],
                [half_size, 0.0, -half_size],
                [-half_size, self.room_size, -half_size],
                [half_size, self.room_size, -half_size],
            ],
            dtype=np.float32,
        )

        vertices = np.concatenate(
            [floor, wall_pos_x, wall_neg_x, wall_pos_z, wall_neg_z], axis=0
        )
        self._grid_vbo = self._renderer.ctx.buffer(vertices.astype("f4"))
        grid_program = self._renderer.shader_manager.get_shader("room_grid")
        self._grid_vao = self._renderer.ctx.vertex_array(
            grid_program,
            [(self._grid_vbo, "3f", "in_position")],
        )

    def _setup_cube_geometry(self):
        half = 0.5
        cube_verts = np.array(
            [
                [-half, -half, half],
                [half, -half, half],
                [half, half, half],
                [-half, -half, half],
                [half, half, half],
                [-half, half, half],
                [half, -half, -half],
                [-half, -half, -half],
                [-half, half, -half],
                [half, -half, -half],
                [-half, half, -half],
                [half, half, -half],
                [-half, half, -half],
                [-half, half, half],
                [half, half, half],
                [-half, half, -half],
                [half, half, half],
                [half, half, -half],
                [-half, -half, half],
                [-half, -half, -half],
                [half, -half, -half],
                [-half, -half, half],
                [half, -half, -half],
                [half, -half, half],
                [half, -half, half],
                [half, -half, -half],
                [half, half, -half],
                [half, -half, half],
                [half, half, -half],
                [half, half, half],
                [-half, -half, -half],
                [-half, -half, half],
                [-half, half, half],
                [-half, -half, -half],
                [-half, half, -half],
                [-half, half, half],
            ],
            dtype=np.float32,
        )
        self._cube_vbo = self._renderer.ctx.buffer(cube_verts.astype("f4"))
        cube_program = self._renderer.shader_manager.get_shader("cube")
        self._cube_vao = self._renderer.ctx.vertex_array(
            cube_program,
            [(self._cube_vbo, "3f", "in_position")],
        )

    def _setup_axis_geometry(self):
        basis_verts, basis_inds = build_axis(
            shaft_radius=0.02,
            shaft_height=0.5,
            head_radius=0.06,
            head_height=0.1,
            segments=16,
            colors={
                "x": np.array([0.9, 0.2, 0.2, 1.0], dtype=np.float32),
                "y": np.array([0.2, 0.85, 0.2, 1.0], dtype=np.float32),
                "z": np.array([0.2, 0.4, 0.95, 1.0], dtype=np.float32),
            },
        )

        self._axis_vert_vbo = self._renderer.ctx.buffer(basis_verts[:, :3].astype("f4"))
        self._axis_color_vbo = self._renderer.ctx.buffer(
            basis_verts[:, 3:].astype("f4")
        )
        self._axis_ibo = self._renderer.ctx.buffer(basis_inds.astype("f4"))

        axis_program = self._renderer.shader_manager.get_shader("axis")
        self._axis_vao = self._renderer.ctx.vertex_array(
            axis_program,
            [
                (self._axis_vert_vbo, "3f", "in_vert"),
                (self._axis_color_vbo, "3f", "in_color"),
            ],
            index_buffer=self._axis_ibo,
        )

    def bind_camera(self, camera):
        pass

    def update(self):
        if not self._renderer:
            return

        viz_window = self._renderer.application
        mouse_x = getattr(viz_window, "mouse_x", 0)
        mouse_y = getattr(viz_window, "mouse_y", 0)

        tile_x = getattr(self, "_tile_x", None)
        if tile_x is None:
            return

        self._focused = (
            tile_x <= mouse_x <= tile_x + self._tile_width
            and self._tile_y <= mouse_y <= self._tile_y + self._tile_height
        )

        if not self._focused:
            return

        keys = getattr(viz_window, "keys_pressed", set())
        if hasattr(viz_window, "wnd") and hasattr(viz_window.wnd, "keys"):
            if hasattr(viz_window.wnd.keys, "A") and hasattr(viz_window.wnd.keys, "D"):
                a_key = viz_window.wnd.keys.A
                d_key = viz_window.wnd.keys.D
                if a_key in keys:
                    self.current_camera = (self.current_camera - 1) % 4
                    viz_window.keys_pressed.discard(a_key)
                if d_key in keys:
                    self.current_camera = (self.current_camera + 1) % 4
                    viz_window.keys_pressed.discard(d_key)

    def draw(self, renderer):
        if renderer is None:
            renderer = self._renderer
        if not renderer:
            return

        renderer.ctx.enable(moderngl.DEPTH_TEST)
        renderer.ctx.enable(moderngl.BLEND)
        renderer.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        camera = self.cameras[self.current_camera]
        mvp = camera.get_vp()

        if self._grid_vao:
            renderer.set_uniform("room_grid", "mvp", mvp.astype("f4").T.tobytes())
            renderer.set_uniform(
                "room_grid", "gRoomCenter", self.room_center.astype("f4").tobytes()
            )
            renderer.set_uniform(
                "room_grid",
                "gRoomSize",
                np.array([self.room_size], dtype="f4").tobytes(),
            )
            renderer.draw("room_grid", [(self._grid_vbo, "3f", "in_position")], None)

        if self._cube_vao and self.assets:
            renderer.set_uniform("cube", "mvp", mvp.astype("f4").T.tobytes())
            for asset in self.assets:
                renderer.set_uniform(
                    "cube", "uOffset", asset["position"].astype("f4").tobytes()
                )
                renderer.set_uniform(
                    "cube", "uScale", np.array([asset["size"]], dtype="f4").tobytes()
                )
                renderer.set_uniform(
                    "cube", "uColor", asset["color"].astype("f4").tobytes()
                )
                renderer.draw("cube", [(self._cube_vbo, "3f", "in_position")], None)

        if self._axis_vao:
            renderer.set_uniform("axis", "mvp", mvp.astype("f4").T.tobytes())
            axis_scale = (self.room_size / 10.0) * 1.5
            renderer.set_uniform(
                "axis", "uScale", np.array([axis_scale], dtype="f4").tobytes()
            )
            renderer.draw(
                "axis",
                [
                    (self._axis_vert_vbo, "3f", "in_vert"),
                    (self._axis_color_vbo, "3f", "in_color"),
                ],
                self._axis_ibo,
            )

        renderer.ctx.disable(moderngl.DEPTH_TEST)

    def compute_room_bounds(self, positions):
        if not positions:
            return

        positions_arr = np.array(positions, dtype=np.float32)
        asset_mins = np.min(positions_arr, axis=0)
        asset_maxs = np.max(positions_arr, axis=0)

        half_size = self.room_size * 0.5
        room_min = self.room_center - half_size
        room_max = self.room_center + half_size

        new_min = np.minimum(room_min, asset_mins)
        new_max = np.maximum(room_max, asset_maxs)

        margin = (new_max - new_min) * self.margin
        new_min -= margin
        new_max += margin

        new_center = (new_min + new_max) / 2.0
        new_size = np.max(new_max - new_min)
        new_size = max(new_size, self.min_size)

        self.room_center = new_center
        self.room_size = new_size

        self._update_camera_positions()
        self._setup_grid_geometry()

    def add_cube(self, position, color, size):
        self.assets.append(
            {
                "position": np.array(position, dtype=np.float32),
                "color": np.array(color, dtype=np.float32),
                "size": size,
            }
        )

        positions = [asset["position"] for asset in self.assets]
        self.compute_room_bounds(positions)
