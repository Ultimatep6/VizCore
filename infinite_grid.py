import moderngl
import numpy as np
import moderngl_window as mglw
from vizcore.utils import *


class InfiniteGridApp(mglw.WindowConfig):
    gl_version = (3, 3)
    window_size = (1024, 768)
    title = "Grid Viewer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        self.grid_program = self.ctx.program(
            vertex_shader="""
            #version 330
            uniform mat4 gVp;
            void main(){
                const vec3 positions[4] = vec3[](
                    vec3(0.5, 0.0, 0.5),
                    vec3(-0.5, 0.0, -0.5),
                    vec3(0.5, 0.0, -0.5),
                    vec3(-0.5, 0.0, 0.5)
                );
                const int Indices[6] = int[6](
                    0,1,2,
                    0,1,3
                );
                int idx = Indices[gl_VertexID];

                gl_Position = gVp * vec4(positions[idx], 1.0);
            }   """,
            fragment_shader="""
            #version 330
            out vec4 FragColor;
            void main(){
                FragColor = vec4(1.0);
            }
            """,
        )
        self.vao = self.ctx.vertex_array(
            self.grid_program,
            [],
        )
        self.update_gvP()

    def update_gvP(self):
        model = np.identity(4)
        view = get_view_matrix(
            eye=np.array([1.0, 1.0, 0.0]),
            target=np.array([0.0, 0.0, 0.0]),
            # up=np.array([0.0, 0.0, 1.0]),
        )
        print(f"View: {view}")
        proj = get_perspective_matrix(
            fov_y_deg=45,
            aspect=self.window_size[0] / self.window_size[1],
            near=0.1,
            far=100,
        )
        print(f"Proj: {proj}")

        gVp = proj @ view @ model

        print(gVp)

        self.grid_program["gVp"].write(gVp.astype("f4").T.tobytes())

    def render(self, time, frame_time):
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.vao.render(moderngl.TRIANGLES, 6)

    def on_render(self, time: float, frame_time: float) -> None:
        self.render(time, frame_time)


if __name__ == "__main__":
    InfiniteGridApp.run()
