import moderngl

from types import SimpleNamespace
import numpy as np
import moderngl_window as mglw
import os
import sys

from vizcore.renderer.camera import Camera
from utils.mesh_loader import load_model, create_example_cube
from vizcore.utils import get_total_rot_matrix, get_model_matrix

from . import settings


class SimulationRoom(mglw.WindowConfig):
    """Simulation room with dynamic bounding box and 4 corner cameras.

    Features:
    - 5-face grid (floor + 4 walls) with LOD-based detail
    - 8 cameras (4 upper, 4 lower corners), switchable with A/D and W/S
    - Origin axis at room center
    - Dynamic second axis that moves around with height indicator
    - Live drone simulation rendered as a mesh
    """

    gl_version = (3, 3)
    window_size = (1024, 768)
    title = "Simulation Room"

    def __init__(
        self,
        axis: bool = True,
        indicator: bool = True,
        beam: bool = True,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.room_center = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.room_size = settings.ROOM_SIZE
        self.min_size = settings.MIN_SIZE
        self.current_camera_index = 0

        # Setup bool
        self._circle_bool = indicator
        self._beam_bool = beam
        self._axis_bool = axis

        # Callbacks
        self.callbacks = SimpleNamespace()
        self.render_callbacks = SimpleNamespace()
        self.ctrl_pressed = False

        self._load_all_shaders()
        self._setup_cameras()
        self._setup_grid_geometry()
        self._setup_axis()

    def _load_all_shaders(self):
        # ----------------------- GRID PROGRAM
        self.grid_program = self.load_program(
            vertex_shader=os.path.join(settings.SHADER_DIR, "sim_grid.vert"),
            fragment_shader=os.path.join(settings.SHADER_DIR, "sim_grid.frag"),
        )

        # ----------------------- MODEL PROGRAM
        self.model_program = self.load_program(
            vertex_shader=os.path.join(settings.SHADER_DIR, "sim_model.vert"),
            fragment_shader=os.path.join(settings.SHADER_DIR, "sim_model.frag"),
        )

        # ----------------------- INDICATOR PROGAM
        self.indicator_program = self.load_program(
            vertex_shader=os.path.join(
                settings.SHADER_DIR, "sim_circle_indicator.vert"
            ),
            fragment_shader=os.path.join(
                settings.SHADER_DIR, "sim_circle_indicator.frag"
            ),
        )

        # ------------------------ CYLINDER BEAM PROGRAM
        self.cylinder_program = self.load_program(
            vertex_shader=os.path.join(settings.SHADER_DIR, "sim_cylinder_beam.vert"),
            fragment_shader=os.path.join(settings.SHADER_DIR, "sim_cylinder_beam.frag"),
            defines={
                "SEGMENTS": settings.CYLINDER_SEGMENT,
                "MAX_INSTANCES": settings.MAX_BODIES,
            },
        )
        # ------------------------ AXIS PROGRAM
        self.axis_program = self.load_program(
            vertex_shader=os.path.join(settings.SHADER_DIR, "sim_arrow.vert"),
            fragment_shader=os.path.join(settings.SHADER_DIR, "sim_arrow.frag"),
            defines={
                "SEGMENTS": settings.ARROW_SEGMENTS,
                "MAX_INSTANCES": settings.MAX_ARROWS,
                "SHAFT_RADIUS": settings.SHAFT_RADIUS,
                "SHAFT_HEIGHT": settings.SHAFT_HEIGHT,
                "HEAD_RADIUS": settings.HEAD_RADIUS,
                "HEAD_HEIGHT": settings.HEAD_HEIGHT,
            },
        )


    def _setup_grid_geometry(self):
        """Build the floor + two wall quads that are always opposite the active camera.

        Wall direction (up vs down) is derived from whether the active camera is in the
        upper ring (indices 0-3) or lower ring (indices 4-7).

        The two vertical walls chosen are always the ones on the FAR side of the room
        from the camera, so they form a backdrop corner behind the origin.
        """
        half_size = self.room_size * 0.5

        # Upper cameras (0-3) look down -> walls go up (+1).
        # Lower cameras (4-7) look up -> walls go down (-1).
        wall_direction = -1 if self.current_camera_index >= 4 else 1
        wall_top = self.room_size * wall_direction

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
                [half_size, wall_top, -half_size],
                [half_size, wall_top, half_size],
                [half_size, 0.0, -half_size],
                [half_size, wall_top, half_size],
                [half_size, 0.0, half_size],
            ],
            dtype=np.float32,
        )

        wall_neg_x = np.array(
            [
                [-half_size, 0.0, half_size],
                [-half_size, wall_top, half_size],
                [-half_size, wall_top, -half_size],
                [-half_size, 0.0, half_size],
                [-half_size, wall_top, -half_size],
                [-half_size, 0.0, -half_size],
            ],
            dtype=np.float32,
        )

        wall_pos_z = np.array(
            [
                [-half_size, 0.0, half_size],
                [half_size, 0.0, half_size],
                [half_size, wall_top, half_size],
                [-half_size, 0.0, half_size],
                [half_size, wall_top, half_size],
                [-half_size, wall_top, half_size],
            ],
            dtype=np.float32,
        )

        wall_neg_z = np.array(
            [
                [half_size, 0.0, -half_size],
                [-half_size, 0.0, -half_size],
                [-half_size, wall_top, -half_size],
                [half_size, 0.0, -half_size],
                [-half_size, wall_top, -half_size],
                [half_size, wall_top, -half_size],
            ],
            dtype=np.float32,
        )

        # Pick the wall on the FAR side from the camera in each axis.
        # Camera in -X half -> show +X wall (wall_pos_x), and vice versa.
        # Camera in -Z half -> show +Z wall (wall_pos_z), and vice versa.
        cam_eye = self.cameras[self.current_camera_index].eye
        center = self.room_center

        x_wall = wall_neg_x if cam_eye[0] > center[0] else wall_pos_x
        z_wall = wall_neg_z if cam_eye[2] > center[2] else wall_pos_z

        vertices = np.concatenate([floor, x_wall, z_wall], axis=0)

        # Release old GPU resources before reallocating
        if hasattr(self, "vbo_grid"):
            self.vbo_grid.release()
        if hasattr(self, "grid_vao"):
            self.grid_vao.release()

        self.vbo_grid = self.ctx.buffer(vertices.astype("f4"))
        self.grid_vao = self.ctx.vertex_array(
            self.grid_program,
            [(self.vbo_grid, "3f", "in_position")],
        )

    def _setup_cameras(self):
        self.cameras = []
        self._default_eye = []
        for _ in range(8):
            camera = Camera(
                window_size=self.window_size,
                eye=np.array([0.0, 0.0, 0.0]),
                move_speed=0.0,
            )
            self.cameras.append(camera)
            self._default_eye.append(np.array([0.0, 0.0, 0.0]))

        self.grid_camera = Camera(
            window_size=self.window_size,
            eye=np.array([0.0, 0.0, 0.0]),
            target=np.array([0.0, 0.0, 0.0]),
            move_speed=0.0,
        )

        self._update_camera_positions()

    def _update_camera_positions(self):
        half_size = self.room_size * 0.5

        upper_positions = [
            np.array([-half_size, self.room_size, -half_size], dtype=np.float32),
            np.array([half_size, self.room_size, -half_size], dtype=np.float32),
            np.array([-half_size, self.room_size, half_size], dtype=np.float32),
            np.array([half_size, self.room_size, half_size], dtype=np.float32),
        ]

        lower_positions = [
            np.array([-half_size, -self.room_size, -half_size], dtype=np.float32),
            np.array([half_size, -self.room_size, -half_size], dtype=np.float32),
            np.array([-half_size, -self.room_size, half_size], dtype=np.float32),
            np.array([half_size, -self.room_size, half_size], dtype=np.float32),
        ]

        for i in range(4):
            self.cameras[i].eye = upper_positions[i] + self.room_center
            self.cameras[i].target = np.array(self.room_center, dtype=np.float32)
            self._default_eye[i] = self.cameras[i].eye.copy()

        for i in range(4):
            self.cameras[i + 4].eye = lower_positions[i] + self.room_center
            self.cameras[i + 4].target = np.array(self.room_center, dtype=np.float32)
            self._default_eye[i + 4] = self.cameras[i + 4].eye.copy()

        self.grid_camera.eye = upper_positions[0] + self.room_center
        self.grid_camera.target = np.array(self.room_center, dtype=np.float32)

    def _setup_axis(self):
        self.axis_vao = self.ctx.vertex_array(self.axis_program, [])
        self.axis_instance_matrices = np.zeros(
            (settings.MAX_ARROWS, 4, 4), dtype=np.float32
        )
        self.axis_instance_colors = np.zeros((settings.MAX_ARROWS, 3), dtype=np.float32)
        self.axis_instance_colors[0] = settings.AXIS_RED
        self.axis_instance_colors[1] = settings.AXIS_GREEN
        self.axis_instance_colors[2] = settings.AXIS_BLUE
        self.axis_vert_count = 12 * settings.ARROW_SEGMENTS
        self._build_circle_geometry()
        self._build_cylinder_geometry()

    def _build_circle_geometry(self):
        self.circle_vao = self.ctx.vertex_array(
            self.indicator_program,
            [],
        )

    def _build_cylinder_geometry(self):
        self.cylinder_vao = self.ctx.vertex_array(self.cylinder_program, [])
        self.max_cylinders = 16
        self.cylinder_instance_matrices = np.zeros(
            (self.max_cylinders, 4, 4), dtype=np.float32
        )
        self.cylinder_instance_colors = np.zeros(
            (self.max_cylinders, 3), dtype=np.float32
        )
        self.cylinder_vert_count = 24 * 6

    def compute_room_bounds(self, assets: list):
        if not assets:
            return

        assets_arr = np.array(assets, dtype=np.float32)
        asset_mins = np.min(assets_arr, axis=0)
        asset_maxs = np.max(assets_arr, axis=0)

        half_size = self.room_size * 0.5
        room_min = self.room_center - half_size
        room_max = self.room_center + half_size

        new_min = np.minimum(room_min, asset_mins)
        new_max = np.maximum(room_max, asset_maxs)

        margin = (new_max - new_min) * settings.WALL_MARGIN
        new_min -= margin
        new_max += margin

        new_center = (new_min + new_max) / 2.0
        new_size = np.max(new_max - new_min)
        new_size = max(new_size, self.min_size)

        self.room_center = new_center
        self.room_size = new_size

        self._update_camera_positions()
        self._setup_grid_geometry()

    def _get_active_camera(self):
        return self.cameras[self.current_camera_index]

    def on_key_event(self, key, action, modifiers):
        if action == self.wnd.keys.ACTION_PRESS and not modifiers.ctrl:
            if key == self.wnd.keys.A:
                base = 0 if self.current_camera_index < 4 else 4
                self.current_camera_index = (
                    base + (self.current_camera_index - base - 1) % 4
                )
                # Walls must update to match the new camera corner
                self._setup_grid_geometry()

            elif key == self.wnd.keys.D:
                base = 0 if self.current_camera_index < 4 else 4
                self.current_camera_index = (
                    base + (self.current_camera_index - base + 1) % 4
                )
                # Walls must update to match the new camera corner
                self._setup_grid_geometry()

            elif key == self.wnd.keys.W:
                if self.current_camera_index >= 4:
                    self.current_camera_index -= 4
                    self._setup_grid_geometry()

            elif key == self.wnd.keys.S:
                if self.current_camera_index < 4:
                    self.current_camera_index += 4
                    self._setup_grid_geometry()

        if key == self.wnd.keys.LEFT_CTRL:
            self.ctrl_pressed = action == self.wnd.keys.ACTION_PRESS

        if cb := getattr(self.callbacks, "on_key_press", None):
            cb(self.ctrl_pressed)

        if cb := getattr(self.callbacks, "on_key_event", None):
            cb(key, action, modifiers)

    def on_mouse_press_event(self, x, y, button):
        if cb := getattr(self.callbacks, "on_mouse_press", None):
            cb(x, y, button)

    def on_mouse_release_event(self, x, y, button):
        if cb := getattr(self.callbacks, "on_mouse_release", None):
            cb(x, y, button)

    def on_mouse_drag_event(self, x, y, dx, dy):
        if cb := getattr(self.callbacks, "on_mouse_drag", None):
            cb(x, y, dx, dy)

    def on_mouse_position_event(self, x, y, dx, dy):
        if cb := getattr(self.callbacks, "on_mouse", None):
            cb(x, y, dx, dy)

    def on_mouse_scroll_event(self, x_offset: float, y_offset: float) -> None:
        if not self.ctrl_pressed:
            for i, camera in enumerate(self.cameras):
                forward = camera.target - camera.eye
                distance = np.linalg.norm(forward)
                if distance < 1e-8:
                    continue

                direction = forward / distance
                raw_step = y_offset * distance * settings.SCROLL_SENSITIVITY

                default_dist = np.linalg.norm(camera.target - self._default_eye[i])
                max_step = distance - default_dist - 1e-4
                step = np.clip(raw_step, None, max_step)

                camera.eye += direction * step
        else:
            # None Main Window functions
            if cb := getattr(self.callbacks, "on_scroll", None):
                cb(x_offset, y_offset)

    def on_resize(self, width, height):
        self.ctx.viewport = (0, 0, width, height)
        if cb := getattr(self.callbacks, "on_resize", None):
            cb(width, height)

    def on_render(self, time, frame_time):

        if cb := getattr(self.callbacks, "on_tick", None):
            cb(time, frame_time)

        camera = self._get_active_camera()
        vp = camera.get_vp()

        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.ctx.color_mask = (True, True, True, True)
        self.ctx.depth_mask = True
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.enable(moderngl.BLEND)

        # ---------------------- Grid Program Setup
        self.grid_program["gVp"].write(vp.astype("f4").T.tobytes())
        self.grid_program["gRoomCenter"].write(self.room_center.astype("f4").tobytes())
        self.grid_program["gRoomSize"].write(
            np.array([self.room_size], dtype="f4").tobytes()
        )
        self.grid_program["gCameraPos"].write(camera.eye.astype("f4").tobytes())
        self.grid_program["gFogDensity"].write(
            np.array([settings.FOG_DENSITY], dtype="f4").tobytes()
        )
        self.grid_program["gGridLineAlpha"].write(
            np.array([settings.GRID_LINE_ALPHA], dtype="f4").tobytes()
        )
        self.grid_program["gGridZoneAlpha"].write(
            np.array([settings.GRID_ZONE_ALPHA], dtype="f4").tobytes()
        )

        self.grid_vao.render(moderngl.TRIANGLES, 18)
        self.ctx.enable(moderngl.DEPTH_TEST)

        # ------------------------------ AXIS SETUP
        if self._axis_bool:
            axis_scale = (
                self.room_size / settings.AXIS_DIVISOR
            ) * settings.AXIS_SCALE_FACTOR
            self.axis_instance_matrices[0] = get_model_matrix(
                sx=axis_scale, sy=axis_scale, sz=axis_scale, rz=-np.pi / 2
            )
            self.axis_instance_matrices[1] = get_model_matrix(
                sx=axis_scale, sy=axis_scale, sz=axis_scale
            )
            self.axis_instance_matrices[2] = get_model_matrix(
                sx=axis_scale, sy=axis_scale, sz=axis_scale, rx=+np.pi / 2
            )

            self.axis_program["u_vp"] = tuple(vp.astype("f4").T.ravel())
            self.axis_program["u_models"].write(
                self.axis_instance_matrices.transpose(0, 2, 1)
                .ravel()
                .astype("f4")
                .tobytes()
            )
            self.axis_program["u_colors"].write(
                self.axis_instance_colors.astype("f4").tobytes()
            )
            self.axis_vao.render(
                moderngl.TRIANGLES, self.axis_vert_count, instances=settings.MAX_ARROWS
            )

        # -------------------------- RENDER BLIPS
        if cb := getattr(self.render_callbacks, "render_nodes", None):
            cb(vp, camera.eye)

        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.depth_mask = False

        if cb := getattr(self.render_callbacks, "render_widgets", None):
            cb()

        if cb := getattr(self.render_callbacks, "render_tileManager", None):
            cb()

        if cb := getattr(self.render_callbacks, "render_guiManager", None):
            cb()

        self.ctx.depth_mask = True
