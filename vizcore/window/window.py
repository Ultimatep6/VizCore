import moderngl
import pyglet
import numpy as np

from vizcore.renderer.renderer import Renderer
from vizcore.widget.baseWidget import BaseWidget
from vizcore.renderer.camera import Camera
from vizcore.renderer.tile import TileManager
from vizcore.bus.data_bus import DataBus
from vizcore.widget.kinematicFrame import KinematicFrame
from vizcore.widget.linePlot import LinePlot
from vizcore.widget.dataTree import DataTree
from vizcore.widget.logConsole import LogConsole
from vizcore.widget.scalarGauge import ScalarGauge

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
        
        # Mouse state for widgets (like SimulationRoom camera controls)
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_dx = 0
        self.mouse_dy = 0
        self.mouse_scroll = 0
        self.mouse_left_pressed = False
        self.mouse_right_pressed = False
        
        # Keyboard state for widgets
        self.keys_pressed = set()

        self._renderer.shader_manager.load_shader(
            "ui",
            vertex_path="vizcore/renderer/shaders/ui.vert",
            fragment_path="vizcore/renderer/shaders/ui.frag"
        )

        self.dragging_border = None
        self.selected_tiles = set()

        self._init_ui_renderer()

        self.bind_events()

    def _init_ui_renderer(self):
        self.ui_vbo = self.ctx.buffer(np.array([0, 0, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1], dtype='f4').tobytes())
        self.ui_outline_vbo = self.ctx.buffer(np.array([0, 0, 1, 0, 1, 0, 1, 1, 1, 1, 0, 1, 0, 1, 0, 0], dtype='f4').tobytes())

        self.add_widget_label = pyglet.text.Label('Add Widget >', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.remove_widget_label = pyglet.text.Label('Remove Widget', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.add_signal_label = pyglet.text.Label('Attach Signal >', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.merge_selected_label = pyglet.text.Label('Merge Selected', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        
        self.kinematic_frame_label = pyglet.text.Label('Kinematic Frame', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.line_plot_label = pyglet.text.Label('Line Plot', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.data_tree_label = pyglet.text.Label('Data Tree Inspector', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.log_console_label = pyglet.text.Label('Log Console', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.scalar_gauge_label = pyglet.text.Label('Scalar Gauge', color=(255, 255, 255, 255), anchor_y='center', font_size=10)
        self.widget_labels = [self.kinematic_frame_label, self.line_plot_label, self.data_tree_label, self.log_console_label, self.scalar_gauge_label]
        
        # Context variables
        self.context_widget = None
        self.context_options = []
        self.signal_labels = []

    def set_Texture(self, texture):
        self.texture = texture
        
    def bind_simulation(self, simulation: object):
        self.simulation = simulation
        # Use initial state to register all signals in dot-notation
        initial_state = self.simulation.get_state()
        self.data_bus.push_payload(initial_state)

    def bind_widget_to_tile(self, tile_idx, widget:BaseWidget):
        widget.bind_renderer(self._renderer)
        # Some widgets manage their own camera, pass renderer info instead
        tile = self.tile_manager.tiles[tile_idx]
        widget.bind_camera(Camera(tile.width, tile.height))
        # Store tile index and position for widgets that need mouse input
        widget._tile_index = tile_idx
        widget._tile_x = tile.x
        widget._tile_y = tile.y
        widget._tile_width = tile.width
        widget._tile_height = tile.height
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

            if i in self.selected_tiles:
                color = (0.3, 0.4, 0.1) if tile.widget is None else (0.2, 0.3, 0.1) # Distinct greenish-colored selection
            else:
                color = (0.1, 0.1, 0.1) if tile.widget is not None else ((0.2, 0.6, 0.9) if i != self.tile_manager.focus_index else (1.0, 0.3, 0.3))

            self._renderer.set_uniform("ui", "u_pos", (draw_x, draw_y))
            self._renderer.set_uniform("ui", "u_size", (draw_w, draw_h))
            self._renderer.set_uniform("ui", "u_color", color)
            self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
            
            if i in self.selected_tiles:
                outline_color = (1.0, 0.5, 0.0) # Orange highlight for selected
            else:
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
            self._renderer.set_uniform("ui", "u_resolution", (self.width, self.height))

            tile = self.tile_manager.tiles[self.popup_tile_idx]
            has_widget = tile.widget is not None

            # Render background boxes with higher "logical" Z-order for UI
            if self.context_options:
                for j, opt in enumerate(self.context_options):
                    box_y = self.popup_y - j * 30
                    self._renderer.set_uniform("ui", "u_pos", (self.popup_x, box_y))
                    self._renderer.set_uniform("ui", "u_size", (140, 30))
                    self._renderer.set_uniform("ui", "u_color", (0.3, 0.3, 0.4) if j % 2 == 0 else (0.25, 0.25, 0.35))
                    self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
                    
                    label = pyglet.text.Label(opt, color=(255, 255, 255, 255), anchor_y='center', font_size=10)
                    label.x = self.popup_x + 10
                    label.y = box_y + 15
                    label.draw()
            else:
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

                if len(self.selected_tiles) == 2:
                    # Option 3 (Top-most box): Merge Selected
                    self._renderer.set_uniform("ui", "u_pos", (self.popup_x, self.popup_y + 30))
                    self._renderer.set_uniform("ui", "u_size", (140, 30))
                    self._renderer.set_uniform("ui", "u_color", (0.1, 0.5, 0.2))
                    self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
                    
                    self.merge_selected_label.x = self.popup_x + 10
                    self.merge_selected_label.y = self.popup_y + 45
                    self.merge_selected_label.draw()

                if not has_widget:
                    self.add_widget_label.x = self.popup_x + 10
                    self.add_widget_label.y = self.popup_y + 15  # 30/2 height
                    self.add_widget_label.draw()
                else:
                    self.add_signal_label.x = self.popup_x + 10
                    self.add_signal_label.y = self.popup_y + 15
                    self.add_signal_label.draw()

                    self.remove_widget_label.x = self.popup_x + 10
                    self.remove_widget_label.y = self.popup_y - 15 # (y - 30) + 15
                    self.remove_widget_label.draw()            # Optional Submenu
            if self.submenu_visible:
                if not has_widget:
                    # Submenu for Available Widgets
                    for j, label in enumerate(self.widget_labels):
                        box_y = self.submenu_y - j*30
                        self._renderer.set_uniform("ui", "u_pos", (self.submenu_x, box_y))
                        self._renderer.set_uniform("ui", "u_size", (140, 30))
                        self._renderer.set_uniform("ui", "u_color", (0.4, 0.4, 0.5) if j % 2 == 0 else (0.35, 0.35, 0.45))
                        self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
                        
                        label.x = self.submenu_x + 10
                        label.y = box_y + 15
                        label.draw()
                else:
                    # Submenu for Available Signals
                    for j, label in enumerate(self.signal_labels):
                        box_y = self.submenu_y - j*30
                        # Draw background
                        self._renderer.set_uniform("ui", "u_pos", (self.submenu_x, box_y))
                        self._renderer.set_uniform("ui", "u_size", (140, 30))
                        self._renderer.set_uniform("ui", "u_color", (0.4, 0.4, 0.5) if j % 2 == 0 else (0.35, 0.35, 0.45))
                        self._renderer.draw("ui", [(self.ui_vbo, "2f", "in_vert")])
                        
                        # Draw Text
                        label.x = self.submenu_x + 10
                        label.y = box_y + 15
                        label.draw()

            self.ctx.enable(moderngl.DEPTH_TEST)

    def update(self, dt):
        if self.simulation is not None and self.is_playing:
            # Check if simulation has a step method (SimNode doesn't mandate it, but the app expects it)
            if hasattr(self.simulation, 'step'):
                self.simulation.step(dt)

            # Optional direct simulation logging hook (not Signal-based)
            if hasattr(self.simulation, 'push_logs'):
                self.simulation.push_logs(self.data_bus)
            
            # Retrieve the whole hierarchical dictionary
            state = self.simulation.get_state()
            # Push the entire tree; DataBus flattens it automatically
            self.data_bus.push_payload(state)

        for tile in self.tile_manager.tiles:
            if tile.widget is not None:
                tile.widget.is_playing = self.is_playing
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
            try:
                print(f"DEBUG WINDOW: mouse press button={button}")
            except Exception as e:
                print(f"ERROR in on_mouse_press: {e}")
            # Update mouse state
            self.mouse_x = x
            self.mouse_y = y
            if button == pyglet.window.mouse.LEFT:
                self.mouse_left_pressed = True
            elif button == pyglet.window.mouse.RIGHT:
                self.mouse_right_pressed = True
                
            if modifiers & pyglet.window.key.MOD_SHIFT and button == pyglet.window.mouse.LEFT:
                for i, tile in enumerate(self.tile_manager.tiles):
                    if tile.x <= x <= tile.x + tile.width and tile.y <= y <= tile.y + tile.height:
                        if len(self.selected_tiles) == 0 and self.tile_manager.focus_index != -1 and self.tile_manager.focus_index != i:
                            # Automatically add the focused tile to start a multi-selection setup
                            self.selected_tiles.add(self.tile_manager.focus_index)
 
                        if i in self.selected_tiles:
                            self.selected_tiles.remove(i)
                        else:
                            if len(self.selected_tiles) < 2:
                                self.selected_tiles.add(i)
                        return

            # Evaluate submenu click
            if self.submenu_visible:
                tile = self.tile_manager.tiles[self.popup_tile_idx] if self.popup_tile_idx != -1 else None
                
                if tile and getattr(tile, 'widget', None) is None:
                    for j, label in enumerate(self.widget_labels):
                        btn_y = self.submenu_y - j*30
                        if self.submenu_x <= x <= self.submenu_x + 140 and btn_y <= y <= btn_y + 30:
                            if button == pyglet.window.mouse.LEFT:
                                if label.text == 'Kinematic Frame':
                                    # Instantiate Kinematic Frame inside Tile 
                                    new_widget = KinematicFrame(channels=5)
                                    self.bind_widget_to_tile(self.popup_tile_idx, new_widget)
                                    for param in ['eulerian_x', 'eulerian_y', 'eulerian_z']:
                                        self.data_bus.push(param, 0.0)
                                    try:
                                        new_widget.bind_external_signal(self.data_bus, [])
                                    except Exception:
                                        pass
                                elif label.text == 'Line Plot':
                                    new_widget = LinePlot(channels=5)
                                    self.bind_widget_to_tile(self.popup_tile_idx, new_widget)
                                elif label.text == 'Data Tree Inspector':
                                    new_widget = DataTree()
                                    self.bind_widget_to_tile(self.popup_tile_idx, new_widget)
                                    new_widget.bind_external_signal(self.data_bus, [])
                                elif label.text == 'Log Console':
                                    new_widget = LogConsole()
                                    self.bind_widget_to_tile(self.popup_tile_idx, new_widget)
                                    new_widget.bind_external_signal(self.data_bus, [])
                                elif label.text == 'Scalar Gauge':
                                    new_widget = ScalarGauge()
                                    self.bind_widget_to_tile(self.popup_tile_idx, new_widget)
                                    new_widget.bind_external_signal(self.data_bus, [])
                            break
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
                self.submenu_mode = None
                return
            
            # Evaluate main popup click
            if self.popup_visible:
                tile = self.tile_manager.tiles[self.popup_tile_idx] if self.popup_tile_idx != -1 else None
                has_widget = tile is not None and getattr(tile, 'widget', None) is not None

                if self.popup_x <= x <= self.popup_x + 140:
                    if self.context_options:
                        if button == pyglet.window.mouse.LEFT:
                            # Evaluate click on dynamic context options
                            for j, opt in enumerate(self.context_options):
                                btn_y = self.popup_y - j * 30
                                if btn_y <= y <= btn_y + 30:
                                    if has_widget and hasattr(tile.widget, 'on_context_menu'):
                                        tile.widget.on_context_menu(opt)
                                    break
                    else:
                        if len(self.selected_tiles) == 2 and self.popup_y + 30 <= y <= self.popup_y + 60:
                            if button == pyglet.window.mouse.LEFT:
                                t1, t2 = list(self.selected_tiles)
                                if self.tile_manager.can_merge(t1, t2):
                                    self.tile_manager.merge(t1, t2)
                                    self._update_all_widgets_cameras()
                                    self.selected_tiles.clear()
                                else:
                                    print("Tiles cannot be merged: Dimensions or borders do not align to form a perfect rectangle.")
                                
                                self.popup_visible = False
                                return

                        elif self.popup_y <= y <= self.popup_y + 30:
                            if button == pyglet.window.mouse.LEFT:
                                self.submenu_visible = True
                                self.submenu_x = self.popup_x + 140
                                self.submenu_mode = 'widget'
                                if has_widget:
                                    # Populate signal list safely using new Shape-Matching logic
                                    self.submenu_y = self.popup_y
                                    self.signal_labels.clear()
                                    if self.simulation:
                                        # Request compatible signal paths from the DataBus
                                        compatible_paths = []
                                        if tile.widget.required_shape:
                                            for shape in tile.widget.required_shape:
                                                compatible_paths.extend(self.data_bus.get_signals_by_shape(shape))
                                        else:
                                            # If widget has no shape contract, show everything
                                            compatible_paths = self.data_bus.list_signals()

                                        for path in compatible_paths:
                                            self.signal_labels.append(pyglet.text.Label(path, color=(255, 255, 255, 255), anchor_y='center', font_size=10))
                                else:
                                    self.submenu_y = self.popup_y
                                return
                        elif self.popup_y - 30 <= y <= self.popup_y:
                            if button == pyglet.window.mouse.LEFT:
                                if has_widget:
                                    self.tile_manager.tiles[self.popup_tile_idx].widget = None
                
                self.context_options = []
                self.popup_visible = False
                self.submenu_visible = False
                self.submenu_mode = None
                return

            # Check if dragging a border
            border = self.tile_manager.get_border_at(x, y, threshold=5)
            if border and button == pyglet.window.mouse.LEFT:
                self.dragging_border = True
                return

            # Normal left click to focus
            if button == pyglet.window.mouse.LEFT and not (modifiers & pyglet.window.key.MOD_SHIFT):
                # Only clear selected_tiles if we aren't clicking inside an active context menu or UI elements
                if not self.popup_visible and not self.submenu_visible:
                    for i, tile in enumerate(self.tile_manager.tiles):
                        if tile.x <= x <= tile.x + tile.width and tile.y <= y <= tile.y + tile.height:
                            self.tile_manager.set_focus(i)
                            self.selected_tiles.clear()
                            # Forward mouse click to widget
                            if tile.widget and hasattr(tile.widget, 'on_mouse_press'):
                                local_x = x - tile.x
                                local_y = y - tile.y
                                tile.widget.on_mouse_press(local_x, local_y, button, modifiers)
                            break

            if button == pyglet.window.mouse.RIGHT:
                for i, tile in enumerate(self.tile_manager.tiles):
                    if tile.x <= x <= tile.x + tile.width and tile.y <= y <= tile.y + tile.height:
                        self.popup_visible = True
                        self.submenu_visible = False
                        self.submenu_mode = None
                        self.popup_x = x
                        self.popup_y = y
                        self.popup_tile_idx = i
                        
                        # Query widget for context menus
                        self.context_options = []
                        if tile.widget and hasattr(tile.widget, 'get_context_menu'):
                            local_x = x - tile.x
                            local_y = y - tile.y
                            options = tile.widget.get_context_menu(local_x, local_y)
                            if options:
                                self.context_options = options
                        break
                        # Query widget for context menus
                        self.context_options = []
                        if tile.widget and hasattr(tile.widget, 'get_context_menu'):
                            local_x = x - tile.x
                            local_y = y - tile.y
                            options = tile.widget.get_context_menu(local_x, local_y)
                            if options:
                                self.context_options = options
                        break

        @self.application.window.event
        def on_mouse_release(x, y, button, modifiers):
            if button == pyglet.window.mouse.LEFT:
                self.dragging_border = False
                self.mouse_left_pressed = False
            elif button == pyglet.window.mouse.RIGHT:
                self.mouse_right_pressed = False

        @self.application.window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            if self.dragging_border and buttons & pyglet.window.mouse.LEFT:
                moved_x, moved_y = self.tile_manager.resize_border(x - dx, y - dy, dx, dy, threshold=15)
                if moved_x != 0 or moved_y != 0:
                    self._update_all_widgets_cameras()
            else:
                for i, tile in enumerate(self.tile_manager.tiles):
                    if tile.x <= x <= tile.x + tile.width and tile.y <= y <= tile.y + tile.height:
                        if tile.widget and hasattr(tile.widget, 'on_mouse_drag'):
                            local_x = x - tile.x
                            local_y = y - tile.y
                            tile.widget.on_mouse_drag(local_x, local_y, dx, dy, buttons, modifiers)
                        break

        @self.application.window.event
        def on_mouse_motion(x, y, dx, dy):
            print(f"DEBUG: on_mouse_motion x={x} y={y}")
            # Update mouse state for widgets
            self.mouse_x = x
            self.mouse_y = y
            self.mouse_dx = dx
            self.mouse_dy = dy
            
            if getattr(self, 'popup_visible', False):
                return
            
            border = self.tile_manager.get_border_at(x, y, threshold=5)
            if border:
                if border[0] == 'vertical':
                    self.application.window.set_mouse_cursor(self.application.window.get_system_mouse_cursor(self.application.window.CURSOR_SIZE_LEFT_RIGHT))
                else:
                    self.application.window.set_mouse_cursor(self.application.window.get_system_mouse_cursor(self.application.window.CURSOR_SIZE_UP_DOWN))
            else:
                self.application.window.set_mouse_cursor(None)

        @self.application.window.event
        def on_mouse_scroll(x, y, scroll_x, scroll_y):
            print(f"DEBUG: on_mouse_scroll x={x} y={y} scroll_y={scroll_y}")
            # Update mouse scroll state
            self.mouse_scroll = scroll_y
            
            for i, tile in enumerate(self.tile_manager.tiles):
                if tile.x <= x <= tile.x + tile.width and tile.y <= y <= tile.y + tile.height:
                    if tile.widget and hasattr(tile.widget, 'on_mouse_scroll'):
                        local_x = x - tile.x
                        local_y = y - tile.y
                        tile.widget.on_mouse_scroll(local_x, local_y, scroll_x, scroll_y)
                    break

        @self.application.window.event
        def on_key_press(symbol, modifiers):
            # Track pressed keys for widgets
            self.keys_pressed.add(symbol)
            
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
            elif symbol == pyglet.window.key.M:
                if len(self.selected_tiles) == 2:
                    t1, t2 = list(self.selected_tiles)
                    if self.tile_manager.can_merge(t1, t2):
                        self.tile_manager.merge(t1, t2)
                        self._update_all_widgets_cameras()
                        self.selected_tiles.clear()
                    else:
                        print("Tiles cannot be merged: Dimensions or borders do not align to form a perfect rectangle.")
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

        @self.application.window.event
        def on_key_release(symbol, modifiers):
            # Remove released keys from tracking
            if symbol in self.keys_pressed:
                self.keys_pressed.remove(symbol)

    def _update_all_widgets_cameras(self):
        for tile in self.tile_manager.tiles:
            if tile.widget is not None and hasattr(tile.widget, 'camera'):
                tile.widget.camera.update_projection(max(1, tile.width), max(1, tile.height))

if __name__ == "__main__":
    width, height = 1920, 1080

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
