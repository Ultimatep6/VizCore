import moderngl
import numpy as np
import moderngl_window as mglw
from vizcore.utils import *
from vizcore.renderer.camera import Camera


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
            uniform vec3 gCameraWorldPos;
            uniform float gGridSize = float(100.0);

            out vec3 WorldPos;
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

                vec3 vPos3 = positions[idx] * gGridSize;
                vPos3.x += gCameraWorldPos.x;
                vPos3.z += gCameraWorldPos.z;

                vec4 vPos4 = vec4(vPos3,1.0);

                gl_Position = gVp * vPos4;
                WorldPos = vPos3;
            }   """,
            fragment_shader="""
            #version 330
            in vec3 WorldPos;
            out vec4 FragColor;

            uniform vec3 gCameraWorldPos;
            uniform float gGridSize;
            uniform float gGridMinPixelsBetweenCells = 2.0;
            uniform float gGridCellSize = 0.1025;
            uniform vec4 gGridColorThin = vec4(0.5,0.5,0.5,1.0);
            uniform vec4 gGridColorThick = vec4(0.0,0.0,0.0,1.0);

            float log10(float x){
                float f = log(x)/log(10.0);
                return f;
                }
            float satf(float x){
                float f = clamp(x,0.0,1.0);
                return f;
            }
            vec2 satv2(vec2 x){
                float f1 = clamp(x.x,0.0,1.0);
                float f2 = clamp(x.y,0.0,1.0);
                return vec2(f1,f2);
            }

            void main(){
                vec2 dvx = vec2(dFdx(WorldPos.x),dFdy(WorldPos.x));
                vec2 dvy = vec2(dFdx(WorldPos.z),dFdy(WorldPos.z));

                float lx = length(dvx);
                float ly = length(dvy);

                vec2 dudv = vec2(lx,ly);

                float l = length(dudv);

                float LOD = max(0.0, log10(l * gGridMinPixelsBetweenCells / gGridCellSize) + 1.0);

                float gGridCellSizeLod0 = gGridCellSize * pow(10.0, floor(LOD));
                float gGridCellSizeLod1 = gGridCellSizeLod0 * 10.0;
                float gGridCellSizeLod2 = gGridCellSizeLod1 * 10.0;

                dudv *= 4.0;

                vec2 temp = mod(WorldPos.xz, gGridCellSizeLod0) / dudv;
                vec2 temp2 = vec2(1.0) - abs(satv2(temp) * 2.0 - vec2(1.0));
                float Lod0a = max(temp2.x, temp2.y);

                temp = mod(WorldPos.xz, gGridCellSizeLod1) / dudv;
                temp2 = vec2(1.0) - abs(satv2(temp) * 2.0 - vec2(1.0));
                float Lod1a = max(temp2.x, temp2.y);

                temp = mod(WorldPos.xz, gGridCellSizeLod2) / dudv;
                temp2 = vec2(1.0) - abs(satv2(temp) * 2.0 - vec2(1.0));
                float Lod2a = max(temp2.x, temp2.y);

                float Lod_fade = fract(LOD);

                vec4 Color;

                if (Lod2a > 0.0) {
                    Color = gGridColorThick;
                    Color.a *= Lod2a;
                } else {
                    if (Lod1a > 0.0) {
                        Color = mix(gGridColorThick,gGridColorThin, Lod_fade);
                        Color.a *= Lod1a;
                    } else {
                        Color = gGridColorThin;
                        Color.a *= (Lod0a * (1.0 - Lod_fade));
                        }
                }

                float OpacityFalloff = (1.0 - satf(length(WorldPos.xz - gCameraWorldPos.xz) / gGridSize));

                Color.a *= OpacityFalloff;
                FragColor = Color;
            }
            """,
        )
        self.vao = self.ctx.vertex_array(
            self.grid_program,
            [],
        )
        self.camera = Camera(
            window_size=self.window_size,
            eye=np.array([0.1, 0.1, 0.0]),
            move_speed=0.01,
        )
        self.keys_pressed = set()
        self.update_gvP()

    def update_gvP(self):
        model = np.identity(4)
        gVp = self.camera.get_vp() @ model
        self.grid_program["gVp"].write(gVp.astype("f4").T.tobytes())

    def update_CameraPos(self):
        pos = self.camera.eye
        self.grid_program["gCameraWorldPos"].write(pos.astype("f4").tobytes())
        self.grid_program["gGridSize"].write(np.array([100.0], dtype="f4").tobytes())
        self.grid_program["gGridMinPixelsBetweenCells"].write(
            np.array([2.0], dtype="f4").tobytes()
        )

    def render(self, time, frame_time):
        self.camera.on_key_press(self.wnd.keys, self.keys_pressed)
        self.update_gvP()
        self.update_CameraPos()
        self.ctx.clear(1.0, 1.0, 1.0, 1.0)
        self.vao.render(moderngl.TRIANGLES, 6)

    def on_render(self, time: float, frame_time: float) -> None:
        self.render(time, frame_time)

    # mouse
    def on_mouse_press_event(self, x, y, button):
        print(f"Mouse button pressed: {button}")

        self.camera.on_mouse_press(button)

    def on_mouse_release_event(self, x, y, button):
        self.camera.on_mouse_release(button)

    def on_mouse_drag_event(self, x, y, dx, dy):
        if self.camera.is_dragging:
            self.camera.on_mouse_drag(x, y)

    def on_key_event(self, key, action, modifiers):
        if action == self.wnd.keys.ACTION_PRESS:
            self.keys_pressed.add(key)
            if key == self.wnd.keys.SPACE:
                print("SPACE key was pressed")
        elif action == self.wnd.keys.ACTION_RELEASE:
            self.keys_pressed.discard(key)
            if key == self.wnd.keys.SPACE:
                print("SPACE key was released")

        if key == self.wnd.keys.Z and modifiers.ctrl:
            print("Ctrl + Z was pressed")


if __name__ == "__main__":
    InfiniteGridApp.run()
