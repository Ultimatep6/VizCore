import pyglet
import moderngl
from pyglet.window import key

class ApplicationWindow(pyglet.window.Window):
    def __init__(self, width=800, height=600, title="VizCore", 
                 fullscreen=False, fullscreen_mode='borderless', renderer=None, 
                 min_width=400, min_height=300, screen_index=None):
        """
        Create application window.
        
        Args:
            fullscreen_mode: 'borderless', 'exclusive', or 'maximized'
                - 'borderless': Borderless window at screen resolution (most compatible)
                - 'exclusive': True fullscreen with mode switch (may cause blanking)
                - 'maximized': Maximized window with borders (safest option)
            screen_index: Which screen to use (0=primary, 1=secondary, etc.). 
                         None=auto-detect largest screen
        """
        
        self.fullscreen_mode = fullscreen_mode
        self._is_fullscreen = fullscreen
        
        # Get all screens and select the appropriate one
        display = pyglet.display.get_display()
        screens = display.get_screens()
        
        if screen_index is not None and 0 <= screen_index < len(screens):
            screen = screens[screen_index]
        else:
            # Auto-detect: use the largest screen (usually the external monitor)
            screen = max(screens, key=lambda s: s.width * s.height)
        
        screen_width = screen.width
        screen_height = screen.height
        
        print(f"Available screens: {len(screens)}")
        for i, s in enumerate(screens):
            print(f"  Screen {i}: {s.width}x{s.height}")
        print(f"Selected screen: {screen_width}x{screen_height}")
        
        if fullscreen:
            if fullscreen_mode == 'borderless':
                # Borderless windowed fullscreen - most compatible
                super().__init__(
                    width=screen_width, 
                    height=screen_height, 
                    caption=title,
                    style=pyglet.window.Window.WINDOW_STYLE_BORDERLESS,
                    resizable=False,
                    screen=screen
                )
                # Position at screen's location
                self.set_location(screen.x, screen.y)
                
            elif fullscreen_mode == 'exclusive':
                # True exclusive fullscreen - may cause display blanking
                super().__init__(
                    width=screen_width, 
                    height=screen_height, 
                    caption=title,
                    fullscreen=True,
                    resizable=False,
                    screen=screen
                )
                
            elif fullscreen_mode == 'maximized':
                # Maximized window - safest option
                super().__init__(
                    width=width, 
                    height=height, 
                    caption=title,
                    resizable=True,
                    screen=screen
                )
                self.maximize()
            else:
                raise ValueError(f"Unknown fullscreen_mode: {fullscreen_mode}")
                
            width = screen_width
            height = screen_height
        else:
            # Normal windowed mode
            super().__init__(
                width=width, 
                height=height, 
                caption=title,
                resizable=True,
                screen=screen
            )

        self.ctx = moderngl.create_context()
        self.layout_engine = None  # Will be set by Dashboard
        self.widgets = []
        self.renderer = renderer  # Will be set by Dashboard after Renderer is created
        self.min_width = min_width
        self.min_height = min_height
        self.selected_screen = screen
        
        # Store original windowed size for toggling back
        self._windowed_width = 1024
        self._windowed_height = 768
        
        # Only set minimum size if not in fullscreen mode
        if not fullscreen:
            self.set_minimum_size(min_width, min_height)

    def on_resize(self, width, height):
        # Skip minimum enforcement in fullscreen mode
        if not self._is_fullscreen:
            # Enforce minimum dimensions
            width = max(width, self.min_width)
            height = max(height, self.min_height)
            
            # If the resize would make window too small, set it back to minimum
            if width < self.min_width or height < self.min_height:
                self.set_size(max(width, self.min_width), max(height, self.min_height))
                return
        
        super().on_resize(width, height)
        
        # Ensure viewport has valid dimensions
        if width > 0 and height > 0:
            self.ctx.viewport = (0, 0, width, height)
        
        # Update renderer's window size for text rendering
        if self.renderer:
            self.renderer.window_size = (width, height)
            # Update text renderers' window size
            if hasattr(self.renderer, 'text'):
                self.renderer.text.window_size = (width, height)
            if hasattr(self.renderer, 'text_title'):
                self.renderer.text_title.window_size = (width, height)
        
        # Notify layout engine which will resize all widgets
        if self.layout_engine:
            self.layout_engine.on_window_resize(width, height)

    def on_key_press(self, symbol, modifiers):
        # Allow ESC or F11 to toggle fullscreen
        if symbol == key.ESCAPE and self._is_fullscreen:
            self.exit_fullscreen()
        elif symbol == key.F11:
            self.toggle_fullscreen()
        
        for widget in self.widgets:
            if hasattr(widget, 'handle_key_event'):
                widget.handle_key_event(symbol, modifiers)

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        if self._is_fullscreen:
            self.exit_fullscreen()
        else:
            self.enter_fullscreen()

    def enter_fullscreen(self):
        """Enter fullscreen mode using the configured fullscreen_mode."""
        if self._is_fullscreen:
            return
            
        # Store current windowed size
        self._windowed_width = self.width
        self._windowed_height = self.height
        
        screen = self.selected_screen
        
        if self.fullscreen_mode == 'borderless':
            # Close current window and create new borderless one
            old_ctx = self.ctx
            old_widgets = self.widgets
            old_layout = self.layout_engine
            old_renderer = self.renderer
            
            # We need to recreate the window with borderless style
            # This is a limitation of pyglet - can't change style after creation
            self.close()
            
            # Create new borderless window
            temp_window = ApplicationWindow(
                width=screen.width,
                height=screen.height,
                title=self.caption,
                fullscreen=True,
                fullscreen_mode='borderless',
                min_width=self.min_width,
                min_height=self.min_height,
                screen_index=None  # Will use same screen selection logic
            )
            
            # Transfer state (this is a workaround - not ideal but functional)
            # In practice, the dashboard would need to handle this transition
            print("Warning: Borderless fullscreen toggle requires window recreation")
            
        elif self.fullscreen_mode == 'exclusive':
            self.set_fullscreen(True, screen)
            
        elif self.fullscreen_mode == 'maximized':
            self.maximize()
        
        self._is_fullscreen = True

    def exit_fullscreen(self):
        """Exit fullscreen and return to windowed mode."""
        if not self._is_fullscreen:
            return
        
        if self.fullscreen_mode == 'borderless':
            # For borderless, we need to recreate window (pyglet limitation)
            # Setting fullscreen=False in constructor will create normal window
            print("Exiting borderless fullscreen - press F11 to toggle back")
            # Just resize and reposition for now
            self.set_size(self._windowed_width, self._windowed_height)
            # Center the window on the screen
            self.set_location(
                self.selected_screen.x + (self.selected_screen.width - self._windowed_width) // 2,
                self.selected_screen.y + (self.selected_screen.height - self._windowed_height) // 2
            )
            
        elif self.fullscreen_mode == 'exclusive':
            self.set_fullscreen(False)
            self.set_size(self._windowed_width, self._windowed_height)
            
        elif self.fullscreen_mode == 'maximized':
            # Just restore to normal window
            self.set_size(self._windowed_width, self._windowed_height)
        
        self.set_minimum_size(self.min_width, self.min_height)
        self._is_fullscreen = False

    def on_draw(self):
        self.clear()
        self.ctx.clear(0.1, 0.1, 0.1)
        for widget in self.widgets:
            if self.renderer:
                widget.draw(self.renderer)

if __name__ == "__main__":
    window = ApplicationWindow()
    pyglet.app.run()