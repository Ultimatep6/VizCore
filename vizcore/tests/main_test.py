import moderngl
import pyglet
import numpy as np
from vizcore.bus.data_bus import DataBus
from vizcore.window.window import Window
from vizcore.components.visualization.kinematicFrame import KinematicFrame

def main():
    width, height = 800, 600
    
    # 1. Setup Pyglet & ModernGL
    window = pyglet.window.Window(width, height, "VizCore Integration Test", resizable=True)
    
    # Important: Create context and enable depth test
    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST | moderngl.CULL_FACE)
    
    # 2. Setup DataBus
    data_bus = DataBus()
    
    # 3. Setup Application State
    app = type('App', (object,), {
        'ctx': ctx, 
        'window': window,
        'data_bus': data_bus
    })()
    
    # 4. Setup VizWindow & Widget
    viz_window = Window(app, width, height)
    
    frame = KinematicFrame(channels=1)
    
    # Correct order:
    # a. Bind to window (which calls bind_renderer internally)
    viz_window.bind_widget(frame)
    # b. Bind to data bus
    frame.bind_external_signal(data_bus, ['velocity'])
    # c. Build geometry
    frame._build_verts()
    
    # 5. Simulation thread/timer
    def update_data():
        t = pyglet.clock.get_default().time()
        # Push some oscillating data
        data_bus.push('eulerian_x', np.sin(t) * 0.5)
        data_bus.push('eulerian_y', np.cos(t) * 0.5)
        data_bus.push('eulerian_z', 0.0)
        
        vec = [np.sin(t * 2), np.cos(t * 2), 0.5]
        data_bus.push('velocity', vec)

    pyglet.clock.schedule_interval(lambda dt: update_data(), 1/60.0)
    
    print("Starting VizCore Integration Test...")
    pyglet.app.run()

    # run for 2 seconds then exit
    pyglet.clock.schedule_once(lambda dt: pyglet.app.exit(), 2.0)

    # print history of velocity signal for debugging
    print("Velocity history:", data_bus.history('velocity'))

if __name__ == "__main__":
    main()
