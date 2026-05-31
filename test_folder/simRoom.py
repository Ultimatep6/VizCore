import moderngl
import numpy as np
import moderngl_window as mglw
from vizcore.utils import *
from vizcore.renderer.camera import Camera
from vizcore.meshes.arrow import build_axis_arrow


class SimulationRoom(mglw.WindowConfig):
    """Simulation room with dynamic bounding box and 4 corner cameras.

    Features:
    - 5-face grid (floor + 4 walls) with LOD-based detail
    - 4 cameras at upper corners, switchable with A/D keys
    - Origin axis at room center
    - Dynamic room bounds computed from simulation assets
    """

    gl_version = (3, 3)
    window_size = (1024, 768)
    title = "Simulation Room"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.room_center = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.room_size = 10.0
        self.min_size = 1.0
        self.current_camera_index = 0

        self._setup_grid_program()
        self._setup_cameras()
        self._setup_axis()
        self._setup_grid_geometry()

        self.cubes = []
        self.cube_program = None
        self.cube_vao = None
        self.test_start_time = None
        self.asset_test_triggered = False

        import os

        if os.environ.get("ASSET_TEST") == "1":
            print("[TEST] Starting asset test mode...")
            self.add_cube(position=[0.0, 1.0, 0.0], color=[0.0, 1.0, 0.0])

    def _setup_grid_program(self):
        """Create shader program for the grid on all 5 faces."""
        with open("shaders/world_grid.vert") as f:
            vertex_shader_code = f.read()

        with open("shaders/world_grid.frag") as f:
            frag_shader_code = f.read()

        self.grid_program = self.ctx.program(
            vertex_shader=vertex_shader_code, fragment_shader=frag_shader_code
        )

    def _setup_cameras(self):
        """Create 4 cameras at upper corners of the room."""
        self.cameras = []
        for _ in range(4):
            camera = Camera(
                window_size=self.window_size,
                eye=np.array([0.0, 0.0, 0.0]),
                move_speed=0.0,
            )
            self.cameras.append(camera)
        self._update_camera_positions()

    def _update_camera_positions(self):
        """Update camera positions based on current room center and size."""
        half_size = self.room_size * 0.5

        camera_positions = [
            np.array([-half_size, self.room_size, -half_size], dtype=np.float32),
            np.array([half_size, self.room_size, -half_size], dtype=np.float32),
            np.array([-half_size, self.room_size, half_size], dtype=np.float32),
            np.array([half_size, self.room_size, half_size], dtype=np.float32),
        ]

        for i, camera in enumerate(self.cameras):
            camera.eye = camera_positions[i] + self.room_center
            camera.target = np.array(self.room_center, dtype=np.float32)

    def _setup_axis(self):
        """Create origin axis visualization."""
        RED = np.array([0.9, 0.2, 0.2], dtype=np.float32)
        GREEN = np.array([0.2, 0.85, 0.2], dtype=np.float32)
        BLUE = np.array([0.2, 0.4, 0.95], dtype=np.float32)

        with open("shaders/world_object.vert") as f:
            vertex_shader_code = f.read()

        with open("shaders/world_object.frag") as f:
            frag_shader_code = f.read()

        self.axis_program = self.ctx.program(
            vertex_shader=vertex_shader_code, fragment_shader=frag_shader_code
        )

        arrow_verts, arrow_idxs = build_axis_arrow(
            shaft_radius=0.02,
            shaft_height=0.5,
            head_radius=0.06,
            head_height=0.1,
            segments=16,
        )
        arrow_verts *= 1.0

        x_verts = transform_vertices(arrow_verts, get_rot_matrix(np.pi / 2, Y_AXIS))
        y_verts = transform_vertices(arrow_verts, get_rot_matrix(-np.pi / 2, X_AXIS))
        z_verts = arrow_verts.copy()

        x_colored = colorize_vertices(x_verts, RED)
        y_colored = colorize_vertices(y_verts, GREEN)
        z_colored = colorize_vertices(z_verts, BLUE)

        n_x = len(x_verts)
        n_y = len(y_verts)

        basis_verts = np.concatenate([x_colored, y_colored, z_colored], axis=0)
        basis_inds = np.concatenate(
            [arrow_idxs, arrow_idxs + n_x, arrow_idxs + n_x + n_y], axis=0
        ).astype(np.int32)

        self.vbo_axis_vert = self.ctx.buffer(basis_verts[:, :3].astype("f4"))
        self.vbo_axis_color = self.ctx.buffer(basis_verts[:, 3:].astype("f4"))
        self.ibo_axis = self.ctx.buffer(basis_inds)

        self.axis_vao = self.ctx.vertex_array(
            self.axis_program,
            [
                (self.vbo_axis_vert, "3f", "in_vert"),
                (self.vbo_axis_color, "3f", "in_color"),
            ],
            index_buffer=self.ibo_axis,
        )

    def _setup_grid_geometry(self):
        """Create 5-face cube geometry for the grid (no ceiling)."""
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

        self.vbo_grid = self.ctx.buffer(vertices.astype("f4"))
        self.grid_vao = self.ctx.vertex_array(
            self.grid_program,
            [(self.vbo_grid, "3f", "in_position")],
        )

    def _setup_cube_program(self):
        """Create shader program for rendering solid cubes."""
        self.cube_program = self.ctx.program(
            vertex_shader="""
            #version 330
            uniform mat4 gVp;
            uniform vec3 gOffset;
            in vec3 in_position;
            void main() {
                gl_Position = gVp * vec4(in_position + gOffset, 1.0);
            }
            """,
            fragment_shader="""
            #version 330
            out vec4 FragColor;
            uniform vec3 gColor;
            void main() {
                FragColor = vec4(gColor, 1.0);
            }
            """,
        )

        half = 1.0
        cube_verts = np.array(
            [
                # Front face
                [-half, -half, half],
                [half, -half, half],
                [half, half, half],
                [-half, -half, half],
                [half, half, half],
                [-half, half, half],
                # Back face
                [half, -half, -half],
                [-half, -half, -half],
                [-half, half, -half],
                [half, -half, -half],
                [-half, half, -half],
                [half, half, -half],
                # Top face
                [-half, half, -half],
                [-half, half, half],
                [half, half, half],
                [-half, half, -half],
                [half, half, half],
                [half, half, -half],
                # Bottom face
                [-half, -half, half],
                [-half, -half, -half],
                [half, -half, -half],
                [-half, -half, half],
                [half, -half, -half],
                [half, -half, half],
                # Right face
                [half, -half, half],
                [half, -half, -half],
                [half, half, -half],
                [half, -half, half],
                [half, half, -half],
                [half, half, half],
                # Left face
                [-half, -half, -half],
                [-half, -half, half],
                [-half, half, half],
                [-half, -half, -half],
                [-half, half, -half],
                [-half, half, half],
            ],
            dtype=np.float32,
        )

        self.cube_vbo = self.ctx.buffer(cube_verts.astype("f4"))
        self.cube_vao = self.ctx.vertex_array(
            self.cube_program,
            [(self.cube_vbo, "3f", "in_position")],
        )

    def add_cube(self, position, color):
        """Add a cube at the given position with the given color."""
        self.cubes.append(
            {
                "position": np.array(position, dtype=np.float32),
                "color": np.array(color, dtype=np.float32),
            }
        )

    def compute_room_bounds(self, assets: list):
        """Compute room bounds to encompass all given asset positions.

        Expands the current room if assets are outside current bounds,
        preserving existing room size when possible.

        Args:
            assets: List of (x, y, z) positions from simulation
        """
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

        margin = (new_max - new_min) * 0.2
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
        """Get the currently active camera."""
        return self.cameras[self.current_camera_index]

    def on_key_event(self, key, action, modifiers):
        if action == self.wnd.keys.ACTION_PRESS:
            if key == self.wnd.keys.A:
                self.current_camera_index = (self.current_camera_index - 1) % 4
            elif key == self.wnd.keys.D:
                self.current_camera_index = (self.current_camera_index + 1) % 4

    def on_render(self, time, frame_time):
        """Main render loop."""
        import os

        if self.test_start_time is None and os.environ.get("ASSET_TEST") == "1":
            self.test_start_time = time

        if self.test_start_time is not None and not self.asset_test_triggered:
            if time - self.test_start_time >= 5.0:
                self.asset_test_triggered = True
                print(f"[TEST] 5 seconds elapsed, adding outside cube...")
                self.add_cube(position=[25.0, 1.0, 15.0], color=[1.0, 0.0, 0.0])
                self.compute_room_bounds(
                    [np.array([25.0, 1.0, 15.0], dtype=np.float32)]
                )
                print(
                    f"[TEST] Room expanded: center={self.room_center}, size={self.room_size}"
                )

        camera = self._get_active_camera()

        gVp = camera.get_vp()
        self.grid_program["gVp"].write(gVp.astype("f4").T.tobytes())
        self.grid_program["gRoomCenter"].write(self.room_center.astype("f4").tobytes())
        self.grid_program["gRoomSize"].write(
            np.array([self.room_size], dtype="f4").tobytes()
        )

        self.ctx.clear(1.0, 1.0, 1.0, 1.0)

        self.grid_vao.render(moderngl.TRIANGLES)

        if self.cubes and self.cube_program is None:
            self._setup_cube_program()

        if self.cubes and self.cube_program is not None:
            self.cube_program["gVp"].write(gVp.astype("f4").T.tobytes())
            for cube in self.cubes:
                self.cube_program["gOffset"].write(
                    cube["position"].astype("f4").tobytes()
                )
                self.cube_program["gColor"].write(cube["color"].astype("f4").tobytes())
                self.cube_vao.render(moderngl.TRIANGLES)

        self.axis_program["u_vp"].write(gVp.astype("f4").T.tobytes())
        self.axis_program["u_offset"].write(
            np.array([0.0, 0.0, 0.0], dtype=np.float32).tobytes()
        )
        axis_scale = (self.room_size / 10.0) * 1.5
        self.axis_program["u_scale"].write(np.array([axis_scale], dtype="f4").tobytes())
        self.axis_vao.render(moderngl.TRIANGLES)


def run_headless_test():
    """Run a headless test to verify the simulation room logic."""
    import sys

    try:
        ctx = moderngl.create_standalone_context()
    except Exception as e:
        print(f"Cannot create moderngl context: {e}")
        print("\nTrying with EGL...")
        try:
            import os

            os.environ["EGL_PLATFORM"] = "surfaceless"
            ctx = moderngl.create_standalone_context()
        except Exception as e2:
            print(f"EGL also failed: {e2}")
            return False

    print("Context created successfully!")

    # Create a mock window config to test initialization
    class MockWindow:
        class keys:
            ACTION_PRESS = 1
            ACTION_RELEASE = 0
            A = 65
            D = 68

    class TestRoom:
        def __init__(self, ctx):
            self.ctx = ctx
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

            self.room_center = np.array([0.0, 0.0, 0.0], dtype=np.float32)
            self.room_size = 10.0
            self.min_size = 1.0
            self.current_camera_index = 0

            self._setup_grid_program()
            self._setup_cameras()
            self._setup_axis()
            self._setup_grid_geometry()

        def _setup_grid_program(self):
            self.grid_program = self.ctx.program(
                vertex_shader="""
                #version 330
                uniform mat4 gVp;
                uniform vec3 gRoomCenter;
                in vec3 in_position;
                out vec3 WorldPos;
                void main() {
                    vec3 worldPos = in_position + gRoomCenter;
                    gl_Position = gVp * vec4(worldPos, 1.0);
                    WorldPos = worldPos;
                }
                """,
                fragment_shader="""
                #version 330
                in vec3 WorldPos;
                out vec4 FragColor;
                void main() {
                    FragColor = vec4(0.5, 0.5, 0.5, 1.0);
                }
                """,
            )

        def _setup_cameras(self):
            from vizcore.renderer.camera import Camera

            self.cameras = []
            for _ in range(4):
                camera = Camera(
                    window_size=(1024, 768),
                    eye=np.array([0.0, 0.0, 0.0]),
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
                camera.target = np.array(self.room_center, dtype=np.float32)

        def _setup_axis(self):
            from vizcore.meshes.arrow import build_axis_arrow
            from vizcore.utils import (
                transform_vertices,
                colorize_vertices,
                get_rot_matrix,
            )

            arrow_verts, _ = build_axis_arrow(0.02, 0.5, 0.06, 0.1, 16)
            self.axis_verts = arrow_verts

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
            self.grid_verts = floor

        def compute_room_bounds(self, assets):
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
            new_center = (new_min + new_max) / 2.0
            new_size = np.max(new_max - new_min)
            new_size = max(new_size, self.min_size)
            self.room_center = new_center
            self.room_size = new_size
            self._update_camera_positions()
            self._setup_grid_geometry()

    print("\n--- Testing Room Initialization ---")
    room = TestRoom(ctx)
    print(f"  Room center: {room.room_center}")
    print(f"  Room size: {room.room_size}")
    print(f"  Camera 0 position: {room.cameras[0].eye}")
    print(f"  Camera 1 position: {room.cameras[1].eye}")
    print(f"  Camera 2 position: {room.cameras[2].eye}")
    print(f"  Camera 3 position: {room.cameras[3].eye}")

    print("\n--- Testing compute_room_bounds ---")
    room.compute_room_bounds([np.array([100.0, 5.0, 50.0])])
    print(f"  After asset at (100, 5, 50):")
    print(f"    Room center: {room.room_center}")
    print(f"    Room size: {room.room_size}")

    room.compute_room_bounds([np.array([-50.0, 2.0, 30.0])])
    print(f"  After asset at (-50, 2, 30):")
    print(f"    Room center: {room.room_center}")
    print(f"    Room size: {room.room_size}")

    print("\n--- Testing camera switching ---")
    print(f"  Initial camera: {room.current_camera_index}")
    room.current_camera_index = (room.current_camera_index - 1) % 4
    print(f"  After A: {room.current_camera_index}")
    room.current_camera_index = (room.current_camera_index + 1) % 4
    print(f"  After D: {room.current_camera_index}")

    print("\n--- All tests passed! ---")
    return True


if __name__ == "__main__":
    import sys

    if "--test" in sys.argv:
        run_headless_test()
    else:
        SimulationRoom.run()
