import moderngl
import numpy as np
import moderngl_window as mglw
from vizcore.meshes.arrow import build_arrow2D
from vizcore.utils import get_rot_matrix


class SimpleWindow2D(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (1024, 768)
    title = "Simple 2D Window"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.program = self.ctx.program(
            vertex_shader="""
            #version 330
            in vec2 in_vert;
            void main() {
                gl_Position = vec4(in_vert, 0.0, 1.0);
            }
            """,
            fragment_shader="""
            #version 330
            out vec4 FragColor;
            void main() {
                FragColor = vec4(1.0, 0.0, 0.0, 1.0);
            }
            """,
        )

        # Build arrow 1 (static)
        vert1, idx1 = build_arrow2D(0.05, 0.5, 0.15, 0.15)
        vert1[:, 0] -= 0.0
        vert1[:, 1] -= 0.25

        # Build arrow 2 (will rotate 90 deg around Z)
        vert2, idx2 = build_arrow2D(0.05, 0.5, 0.15, 0.15)
        vert2[:, 0] -= 0.0
        vert2[:, 1] -= 0.25
        # Offset arrow 2 to the right
        vert2[:, 0] += 0.3

        # Rotate arrow 2 by 90 degrees around Z
        rot_mat = get_rot_matrix(np.deg2rad(90), np.array([0.0, 0.0, 1.0]))
        # Convert to 4D homogeneous coordinates (x, y, 0, 1)
        vert2_4d = np.pad(vert2, ((0, 0), (0, 2)), mode="constant", constant_values=0.0)
        vert2_4d[:, 3] = 1.0
        rotated = vert2_4d @ rot_mat.T
        vert2 = rotated[:, :2]

        # Shift shaft2 to match bottom right of arrow 1
        vert2 += vert1[1] - vert2[0]

        # Combine vertices
        self.verts = np.concatenate([vert1, vert2])

        # Adjust indices for arrow 2
        idx2 += len(vert1)
        self.idxs = np.concatenate([idx1, idx2])

        self.vbo = self.ctx.buffer(self.verts.astype("f4"))
        self.ibo = self.ctx.buffer(self.idxs.astype("i4"))
        self.vao = self.ctx.vertex_array(
            self.program, [(self.vbo, "2f", "in_vert")], index_buffer=self.ibo
        )

    def on_render(self, time, frame_time):
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.vao.render(moderngl.TRIANGLES)


if __name__ == "__main__":
    SimpleWindow2D.run()
