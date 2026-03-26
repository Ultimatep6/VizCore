import numpy as np
from vizcore.widgets.base_widget import BaseWidget
from vizcore.layout.rect import Rect


class BarMeter(BaseWidget):
    """
    Displays scalar value as vertical or horizontal bar.

    Responsibilities:
        - Visualize actuator outputs
        - Display scalar values with visual feedback

    Features:
        - Configurable ranges
        - Vertical or horizontal orientation
        - Color coding based on value
    """
    def __init__(self, v_max, v_min, orientation='vertical', title=None):
        """
        Initialize BarMeter widget.
        
        Args:
            v_max: Maximum value for the bar
            v_min: Minimum value for the bar
            orientation: 'vertical' or 'horizontal'
            title: Optional title displayed above/beside the bar
        """
        super().__init__()
        self.v_max = v_max
        self.v_min = v_min
        self.orientation = orientation
        self.title = title
        self.value = v_min
        self.data_bus = None
        self.signal_name = None

    def update(self, data=None):
        """Update the bar meter value from the data bus."""
        if self.data_bus and self.signal_name:
            latest = self.data_bus.latest(self.signal_name)
            if latest is not None:
                self.value = np.clip(latest, self.v_min, self.v_max)

    def draw_lines(self, renderer):
        """Draw the bar meter."""
        if not self.rect:
            return

        # Calculate bar dimensions based on orientation
        margin = 40
        bar_thickness = 50
        
        if self.orientation == 'vertical':
            # Reserve space for title, value, and labels
            title_space = 80 if self.title else 40
            bottom_space = 60  # Space for min label and value
            
            # Vertical bar positioned in center
            bar_x = self.rect.x + (self.rect.width - bar_thickness) // 2
            bar_y = self.rect.y + bottom_space
            bar_width = bar_thickness
            bar_height = self.rect.height - title_space - bottom_space
            
            # Draw background (empty bar)
            renderer.draw_rect(bar_x, bar_y, bar_width, bar_height, 
                             color=(0.2, 0.2, 0.2, 1.0))
            
            # Calculate filled portion (fill from BOTTOM to TOP)
            value_normalized = (self.value - self.v_min) / (self.v_max - self.v_min + 1e-6)
            value_normalized = np.clip(value_normalized, 0.0, 1.0)
            filled_height = bar_height * value_normalized
            
            # Color based on value (green -> yellow -> red)
            if value_normalized < 0.5:
                color = (0.0, 1.0, 0.0, 1.0)  # Green
            elif value_normalized < 0.8:
                color = (1.0, 1.0, 0.0, 1.0)  # Yellow
            else:
                color = (1.0, 0.0, 0.0, 1.0)  # Red
            
            # Draw filled bar FROM BOTTOM (key fix here!)
            renderer.draw_rect(bar_x, bar_y, bar_width, filled_height, color=color)
            
            # Draw border
            border_thickness = 3
            # Top border
            renderer.draw_rect(bar_x - border_thickness, bar_y + bar_height, 
                             bar_width + 2 * border_thickness, border_thickness,
                             color=(0.8, 0.8, 0.8, 1.0))
            # Bottom border
            renderer.draw_rect(bar_x - border_thickness, bar_y - border_thickness, 
                             bar_width + 2 * border_thickness, border_thickness,
                             color=(0.8, 0.8, 0.8, 1.0))
            # Left border
            renderer.draw_rect(bar_x - border_thickness, bar_y, 
                             border_thickness, bar_height,
                             color=(0.8, 0.8, 0.8, 1.0))
            # Right border
            renderer.draw_rect(bar_x + bar_width, bar_y, 
                             border_thickness, bar_height,
                             color=(0.8, 0.8, 0.8, 1.0))
            
        else:
            # Horizontal bar
            title_space = 80 if self.title else 20
            left_space = 80  # Space for min label
            right_space = 80  # Space for max label
            
            bar_x = self.rect.x + left_space
            bar_y = self.rect.y + (self.rect.height - bar_thickness) // 2
            bar_width = self.rect.width - left_space - right_space
            bar_height = bar_thickness
            
            # Adjust for title
            if self.title:
                bar_y -= 20
            
            # Draw background (empty bar)
            renderer.draw_rect(bar_x, bar_y, bar_width, bar_height, 
                             color=(0.2, 0.2, 0.2, 1.0))
            
            # Calculate filled portion (fill from LEFT to RIGHT)
            value_normalized = (self.value - self.v_min) / (self.v_max - self.v_min + 1e-6)
            value_normalized = np.clip(value_normalized, 0.0, 1.0)
            filled_width = bar_width * value_normalized
            
            # Color based on value (green -> yellow -> red)
            if value_normalized < 0.5:
                color = (0.0, 1.0, 0.0, 1.0)  # Green
            elif value_normalized < 0.8:
                color = (1.0, 1.0, 0.0, 1.0)  # Yellow
            else:
                color = (1.0, 0.0, 0.0, 1.0)  # Red
            
            # Draw filled bar FROM LEFT
            renderer.draw_rect(bar_x, bar_y, filled_width, bar_height, color=color)
            
            # Draw border
            border_thickness = 3
            # Top border
            renderer.draw_rect(bar_x - border_thickness, bar_y + bar_height, 
                             bar_width + 2 * border_thickness, border_thickness,
                             color=(0.8, 0.8, 0.8, 1.0))
            # Bottom border
            renderer.draw_rect(bar_x - border_thickness, bar_y - border_thickness, 
                             bar_width + 2 * border_thickness, border_thickness,
                             color=(0.8, 0.8, 0.8, 1.0))
            # Left border
            renderer.draw_rect(bar_x - border_thickness, bar_y, 
                             border_thickness, bar_height,
                             color=(0.8, 0.8, 0.8, 1.0))
            # Right border
            renderer.draw_rect(bar_x + bar_width, bar_y, 
                             border_thickness, bar_height,
                             color=(0.8, 0.8, 0.8, 1.0))

    def draw_text(self, renderer):
        """Draw title and value labels."""
        if not self.rect:
            return
        
        cx = self.rect.x + self.rect.width // 2
        
        if self.orientation == 'vertical':
            # Draw title at the top
            if self.title:
                y = self.rect.y + self.rect.height - 50
                renderer.draw_text_centered(self.title, cx, y)
            
            # Draw current value at the very top
            value_text = f"{self.value:.2f}"
            y = self.rect.y + self.rect.height - 25
            renderer.draw_text_centered(value_text, cx, y)
            
            # Draw max label at top of bar
            max_text = f"{self.v_max:.1f}"
            label_x = self.rect.x + self.rect.width // 2 + 40
            y_max = self.rect.y + self.rect.height - 140
            renderer.draw_text(max_text, label_x, y_max)
            
            # Draw min label at bottom of bar
            min_text = f"{self.v_min:.1f}"
            y_min = self.rect.y + 60
            renderer.draw_text(min_text, label_x, y_min)
            
        else:
            # Draw title above the bar
            if self.title:
                y = self.rect.y + self.rect.height - 40
                renderer.draw_text_centered(self.title, cx, y)
            
            # Draw current value below the bar
            value_text = f"{self.value:.2f}"
            y = self.rect.y + 10
            renderer.draw_text_centered(value_text, cx, y)
            
            # Draw min label at left of bar
            min_text = f"{self.v_min:.1f}"
            renderer.draw_text(min_text, self.rect.x + 10, 
                             self.rect.y + self.rect.height // 2 - 10)
            
            # Draw max label at right of bar
            max_text = f"{self.v_max:.1f}"
            renderer.draw_text(max_text, self.rect.x + self.rect.width - 70, 
                             self.rect.y + self.rect.height // 2 - 10)

    def draw(self, renderer):
        """Draw the complete bar meter."""
        self.draw_lines(renderer)
        self.draw_text(renderer)

    def resize(self, rect):
        """Update widget rectangle."""
        super().resize(rect)

    def bind_signal(self, data_bus, signal):
        """Bind this bar meter to a signal from the data bus."""
        self.signal_name = signal
        self.data_bus = data_bus