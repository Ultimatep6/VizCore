import moderngl
import pyglet
import numpy as np

from vizcore.renderer.renderer import Renderer
from vizcore.widget.baseWidget import BaseWidget
from vizcore.renderer.camera import Camera
from vizcore.renderer.tile import TileManager
from vizcore.bus.data_bus import DataBus
from vizcore.widget.kinematicFrame import KinematicFrame
from vizcore.simulation.simulation import BaseSimulation


class Window:
    def __init__(self, application: object, width: int, height: int):
        self.application = application
        self.ctx = application.ctx
        self.width = width
        self.height = height

        self._renderer = Renderer(application, (width, height))
        self.data_bus = DataBus()

        self.tile_manager = TileManager(width, height)

        self.simulation = None
        self.is_playing = False

        # UI context menu variables
        self.popup_visible = False
        self.popup_x = 0
        self.popup_y = 0
        self.popup_tile_idx = -1

        # Interactive Sub Menu States
        self.submenu_visible = False
        self.submenu_x = 0
        self.submenu_y = 0

        self._renderer.shader_manager.load_shader(
            "ui",
            vertex_path="vizcore/renderer/shaders/ui.vert",
            fragment_path="vizcore/renderer/shaders/ui.frag"
        )

        self._init_ui_renderer()

        self.bind_events()

    def _init_ui_renderer(self):
        self.ui_vbo = self.ctx.buffer(np.array([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1], dtype='f4').tobytes())
        self.ui_outline_vbo = self.ctx.buffer(np.array([0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0], dtype='f4').tobytes())

        self.add_widget_label = pyglet.text.Label('Add Widget >', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.remove_widget_label = pyglet.text.Label('Remove Widget', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.add_signal_label = pyglet.text.Label('Attach Signal >', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.kinematic_frame_label = pyglet.text.Label('Kinematic Frame', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        
        # Dynamic signal labels created on-demand when submenu is active
        self.signal_labels = []

    def set_Texture(self, texture):
        self.texture = texture
        
    def bind_simulation(self, simulation: BaseSimulation):
        self.simulation = simulation
        for signal_name in simulation.exposed_signals:
            self.data_bus.register_signal(signal_name)
            
        # Push the initialized state immediately so widgets can evaluate
        # signal dimensionality before the user presses "Play"
        initial_state = self.simulation.get_state()
        for key, val in initial_state.items():
            self.data_bus.push(key, val)

    def bind_widget_to_tile(self, tile_idx, widget:BaseWidget):
        widget.bind_renderer(self._renderer)
        widget.bind_camera(Camera(self.tile_manager.tiles[tile_idx].width, self.tile_manager.tiles[tile_idx].height))
        self.tile_manager.tiles[tile_idx].widget = widget

    def render(self):
        # 1. First, render the tile background UI components
        # Note: we temporarily disable depth test for 2d UI rendering
        self.ctx.disable(moderngl.DEPTH_TEST)
        self._renderer.set_uniform("ui", "u_resolution", (self.width, self.height))

        for i, tile in enumerate(self.tile_manager.tiles):
            margin = 2
            draw_x = tile.x + margin
            draw_y = tile.y + margin
            draw_w = max(1, tile.width - 2 * margin)
            draw_h = max(1, tile.height - 2 * margin)

            color = (0.1, 0.1, 0.1) if tile.widget is not None else ((0.2, 0.6, 0.9) if i != self.tile_manager.focus_index else (1.0, 0.3, 0.3))

            self._renderer.set_uniform("ui", "u_pos", (draw_x, draw_y))
            self._renderer.set_uniform("ui", "u_size", (draw_w, draw_h))
            self._renderer.set_uniform("ui", "u_color", color)
            self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
            
            outline_color = (1.0, 1.0, 1.0) if i != self.tile_manager.focus_index else (1.0, 1.0, 0.0)
            self._renderer.set_uniform("ui", "u_color", outline_color)
            self._renderer.draw("ui", [(self.ui_outline_vbo, "2f", "in_vert")], mode=moderngl.LINES)

        # 2. Iterate through tiles and render their 3d widgets using Viewports
        self.ctx.enable(moderngl.DEPTH_TEST)
        for i, tile in enumerate(self.tile_manager.tiles):
            if tile.widget is not None:
                margin = 2
                self.ctx.viewport = (tile.x + margin, tile.y + margin, tile.width - 2 * margin, tile.height - 2 * margin)
                tile.widget.draw(self._renderer)
        
        # Restore full viewport for overlays
        self.ctx.viewport = (0, 0, self.width, self.height)

        # 3. Draw Context popups
        if self.popup_visible:
            self.ctx.disable(moderngl.DEPTH_TEST)
            tile = self.tile_manager.tiles[self.popup_tile_idx]
            has_widget = tile.widget is not None

            # Option 1 (Top box): Add Widget OR Attach Signal
            self._renderer.set_uniform("ui", "u_pos", (self.popup_x, self.popup_y))
            self._renderer.set_uniform("ui", "u_size", (140, 30))
            self._renderer.set_uniform("ui", "u_color", (0.3, 0.3, 0.3))
            self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])

            # Option 2 (Bottom box): Blank OR Remove Widget
            self._renderer.set_uniform("ui", "u_pos", (self.popup_x, self.popup_y - 30))
            self._renderer.set_uniform("ui", "u_size", (140, 30))
            self._renderer.set_uniform("ui", "u_color", (0.2, 0.2, 0.2))
            self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])

            if not has_widget:
                self.add_widget_label.x = self.popup_x + 10
                self.add_widget_label.y = self.popup_y + 15
                self.add_widget_label.draw()
            else:
                self.add_signal_label.x = self.popup_x + 10
                self.add_signal_label.y = self.popup_y + 15
                self.add_signal_label.draw()

                self.remove_widget_label.x = self.popup_x + 10
                self.remove_widget_label.y = self.popup_y - 15
                self.remove_widget_label.draw()

            # Optional Submenu
            if self.submenu_visible:
                if not has_widget:
                    # Submenu for Sub Widget
                    self._renderer.set_uniform("ui", "u_pos", (self.submenu_x, self.submenu_y))
                    self._renderer.set_uniform("ui", "u_size", (140, 30))
                    self._renderer.set_uniform("ui", "u_color", (0.4, 0.4, 0.5))
                    self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
                    self.kinematic_frame_label.x = self.submenu_x + 10
                    self.kinematic_frame_label.y = self.submenu_y + 15
                    self.kinematic_frame_label.draw()
                else:
                    # Submenu for Available Signals
                    for j, label in enumerate(self.signal_labels):
                        # Draw background
                        self._renderer.set_uniform("ui", "u_pos", (self.submenu_x, self.submenu_y - j*30))
                        self._renderer.set_uniform("ui", "u_size", (140, 30))
                        self._renderer.set_uniform("ui", "u_color", (0.4, 0.4, 0.5) if j % 2 == 0 else (0.35, 0.35, 0.45))
                        self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
                        
                        # Draw Text
                        label.x = self.submenu_x + 10
                        label.y = self.submenu_y - j * 30 + 15
                        label.draw()

            self.ctx.enable(moderngl.DEPTH_TEST)

    def update(self, dt):
        if self.simulation is not None and self.is_playing:
            self.simulation.step(dt)
            state = self.simulation.get_state()
            for key, val in state.items():
                self.data_bus.push(key, val)

        for tile in self.tile_manager.tiles:
            if tile.widget is not None:
                tile.widget.update()

    def on_draw(self):
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)
        self.render()

    def bind_events(self):
        @self.application.window.event
        def on_draw():
            self.on_draw()

        @self.application.window.event
        def on_mouse_press(x, y, button, modifiers):
            # Evaluate submenu click
            if self.submenu_visible:
                tile = self.tile_manager.tiles[self.popup_tile_idx] if self.popup_tile_idx != -1 else None

                if tile and getattr(tile, 'widget', None) is None:
                    if self.submenu_x <= x <= self.submenu_x + 140 and self.submenu_y <= y <= self.submenu_y + 30:
                        if button == pyglet.window.mouse.LEFT:
                            # Instantiate Kinematic Frame inside Tile 
                            # Preallocate channels=5 so we have room for dynamic custom signals
                            new_widget = KinematicFrame(channels=5)
                            self.bind_widget_to_tile(self.popup_tile_idx, new_widget)
                            for param in ['eulerian_x', 'eulerian_y', 'eulerian_z']:
                                self.data_bus.push(param, 0.0)
                            try:
                                new_widget.bind_external_signal(self.data_bus, [])
                            except Exception:
                                pass
                else:
                    if tile:
                        # Iterate backwards over dynamically created signal tags to check hitbox
                        for j, label in enumerate(self.signal_labels):
                            btn_y = self.submenu_y - j*30
                            if self.submenu_x <= x <= self.submenu_x + 140 and btn_y <= y <= btn_y + 30:
                                if button == pyglet.window.mouse.LEFT:
                                    sig_name = label.text
                                    tile.widget.bind_external_signal(self.data_bus, [sig_name])
                                    break

                self.submenu_visible = False
                self.popup_visible = False
                return
            
            # Evaluate main popup click
            if self.popup_visible:
                tile = self.tile_manager.tiles[self.popup_tile_idx] if self.popup_tile_idx != -1 else None
                has_widget = tile is not None and getattr(tile, 'widget', None) is not None

                if self.popup_x <= x <= self.popup_x + 140:
                    if self.popup_y <= y <= self.popup_y + 30:
                        if button == pyglet.window.mouse.LEFT:
                            self.submenu_visible = True
                            self.submenu_x = self.popup_x + 140
                            if has_widget:
                                # Populate signal list safely
                                self.submenu_y = self.popup_y
                                self.signal_labels.clear()
                                if self.simulation:
                                    for sig in self.simulation.exposed_signals:
                                        # Only display signals that the active widget explicitly supports 
                                        if sig not in ['eulerian_x', 'eulerian_y', 'eulerian_z']:
                                            if tile.widget.accepts_signal(self.data_bus, sig):
                                                self.signal_labels.append(pyglet.text.Label(sig, color=(255, 255, 255, 255), anchor_y='center', font_size=10))
                            else:
                                self.submenu_y = self.popup_y
                            return
                    elif self.popup_y - 30 <= y <= self.popup_y:
                        if button == pyglet.window.mouse.LEFT:
                            if has_widget:
                                self.tile_manager.tiles[self.popup_tile_idx].widget = None
                
                self.popup_visible = False
                self.submenu_visible = False
                return

            if button == pyglet.window.mouse.RIGHT:
                for i, tile in enumerate(self.tile_manager.tiles):
                    if tile.x <= x <= tile.x + tile.width and tile.y <= y <= tile.y + tile.height:
                        self.popup_visible = True
                        self.submenu_visible = False
                        self.popup_x = x
                        self.popup_y = y
                        self.popup_tile_idx = i
                        break

        @self.application.window.event
        def on_key_press(symbol, modifiers):
            if symbol == pyglet.window.key.SPACE:
                self.is_playing = not self.is_playing
                print(f"Simulation Playing: {self.is_playing}")
                return
            elif symbol == pyglet.window.key.V:
                self.tile_manager.split_focused_tile('vertical')
                self._update_all_widgets_cameras()
            elif symbol == pyglet.window.key.H:
                self.tile_manager.split_focused_tile('horizontal')
                self._update_all_widgets_cameras()
            else:
                idx = self.tile_manager.focus_index
                current = self.tile_manager.tiles[idx]
                next_focus = idx
                
                def y_overlaps(t1, t2): return max(t1.y, t2.y) < min(t1.y + t1.height, t2.y + t2.height)
                def x_overlaps(t1, t2): return max(t1.x, t2.x) < min(t1.x + t1.width, t2.x + t2.width)

                if symbol == pyglet.window.key.RIGHT:
                    for i, tile in enumerate(self.tile_manager.tiles):
                        if i != idx and tile.x == current.x + current.width and y_overlaps(current, tile):
                            next_focus = i
                            break
                elif symbol == pyglet.window.key.DOWN:
                    for i, tile in enumerate(self.tile_manager.tiles):
                        if i != idx and tile.y + tile.height == current.y and x_overlaps(current, tile):
                            next_focus = i
                            break
                elif symbol == pyglet.window.key.LEFT:
                    for i, tile in enumerate(self.tile_manager.tiles):
                        if i != idx and tile.x + tile.width == current.x and y_overlaps(current, tile):
                            next_focus = i
                            break
                elif symbol == pyglet.window.key.UP:
                    for i, tile in enumerate(self.tile_manager.tiles):
                        if i != idx and tile.y == current.y + current.height and x_overlaps(current, tile):
                            next_focus = i
                            break
                self.tile_manager.set_focus(next_focus)

    def _update_all_widgets_cameras(self):
        for tile in self.tile_manager.tiles:
            if tile.widget is not None and hasattr(tile.widget, 'camera'):
                tile.widget.camera.update_projection(max(1, tile.width), max(1, tile.height))

if __name__ == "__main__":
    width, height = 800, 600

    window = pyglet.window.Window(width, height, "Tile Windows & Widgets")
    window.switch_to()

    ctx = moderngl.create_context()
    ctx.enable(moderngl.DEPTH_TEST)
    ctx.viewport = (0, 0, width, height)

    app = type('App', (object,), {'ctx': ctx, 'window': window})()

    viz_window = Window(app, width, height)

    # Create and bind the simulation
    from vizcore.simulation.simulation import AttitudeControlSim
    sim = AttitudeControlSim()
    viz_window.bind_simulation(sim)

    # Schedule the update loop
    pyglet.clock.schedule_interval(viz_window.update, 1/60.0)

    pyglet.app.run()
