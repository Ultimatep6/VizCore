import moderngl
import numpy as np
import moderngl_window as mglw
from vizcore.meshes.arrow import build_arrow2D
from vizcore.renderer.camera import Camera


class SimpleWindow3D(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (1024, 768)
    title = "Simple 3D Window"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.camera = Camera(
            window_size=self.window_size, eye=np.array([1.0, 1.0, 1.0])
        )

        self.program = self.ctx.program(
            vertex_shader="""
            #version 330
            uniform mat4 u_vp;
            in vec4 in_vert;
            in float in_arrow_id;

            void main() {
                vec4 pos = in_vert;
                
                if (in_arrow_id == 1.0) {
                    float temp = pos.x;
                    pos.x = -pos.y;
                    pos.y = temp;
                }
                else if (in_arrow_id == 2.0) {
                    float temp = pos.y;
                    pos.y = pos.z;
                    pos.z = -temp;
                }
                
                gl_Position = u_vp * pos;
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

        arrow_verts, arrow_idxs = build_arrow2D(0.05, 0.5, 0.15, 0.15, as_3d=True)
        verts_per_arrow = len(arrow_verts)
        num_arrows = 3

        all_verts = np.tile(arrow_verts, (num_arrows, 1))
        arrow_ids = np.array(
            [i // verts_per_arrow for i in range(len(all_verts))], dtype="f4"
        )

        all_idxs = np.concatenate(
            [arrow_idxs + i * verts_per_arrow for i in range(num_arrows)]
        )

        self.vbo_vert = self.ctx.buffer(all_verts.astype("f4"))
        self.vbo_arrow_id = self.ctx.buffer(arrow_ids.astype("f4"))
        self.ibo = self.ctx.buffer(all_idxs.astype("i4"))

        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo_vert, "4f", "in_vert"), (self.vbo_arrow_id, "f", "in_arrow_id")],
            index_buffer=self.ibo,
        )

    def on_render(self, time, frame_time):
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)

        vp = self.camera.get_vp()
        self.program["u_vp"].write(vp.astype("f4").T.tobytes())

        self.vao.render(moderngl.TRIANGLES)


if __name__ == "__main__":
    SimpleWindow3D.run()
