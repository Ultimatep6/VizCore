# vizcore/app/run.py
"""
Demo script showing LinePlot with axis labels and fullscreen modes.

This example demonstrates:
- Plot title at the top
- X-axis label at the bottom (horizontal)
- Y-axis label on the left (rotated 90 degrees)
- Fullscreen mode support with different modes
- Multi-monitor support

Fullscreen modes:
- 'borderless': Borderless window at screen resolution (RECOMMENDED - most compatible)
- 'exclusive': True fullscreen with mode switch (may cause blanking on some monitors)
- 'maximized': Maximized window with borders (safest option)

Screen selection:
- screen_index=None: Auto-detect largest screen (usually external monitor)
- screen_index=0: Primary screen (usually laptop screen)
- screen_index=1: Secondary screen (usually external monitor)
"""
import numpy as np
import time
from vizcore.app.dashboard import Dashboard
from vizcore.layout.rect import Rect
from vizcore.widgets.plots.line_plot import LinePlot

# Choose your fullscreen mode here:
FULLSCREEN_MODE = 'maximized'  # 'borderless', 'exclusive', or 'maximized'

# Choose your screen:
# None = auto-detect largest (recommended for laptop + external monitor setups)
# 0 = primary screen (usually laptop)
# 1 = secondary screen (usually external monitor)
SCREEN_INDEX = None  # Auto-detect largest screen

dashboard = Dashboard(
    title="Line Plot with Axis Labels", 
    rows=2, 
    cols=2, 
    fullscreen=True,
    fullscreen_mode=FULLSCREEN_MODE,
    screen_index=SCREEN_INDEX
)

# Create plots with title and axis labels
plot1 = LinePlot(
    channels=1, 
    buffer_size=256, 
    margin=50, 
    title="Sine Wave",
    x_label="Time (s)",
    y_label="Amplitude"
)

plot2 = LinePlot(
    channels=1, 
    buffer_size=256, 
    margin=50, 
    title="Cosine Wave",
    x_label="Time (s)",
    y_label="Amplitude"
)

plot3 = LinePlot(
    channels=1, 
    buffer_size=256, 
    margin=50, 
    title="Random Noise",
    x_label="Sample Number",
    y_label="Value"
)

# Add widgets to dashboard
dashboard.add_widget(plot1, row=0, col=0, signal="ch1")
dashboard.add_widget(plot2, row=0, col=1, signal="ch2")
dashboard.add_widget(plot3, row=1, col=0, signal="ch3")

# Simulation update function
t0 = time.time()
def sim_update():
    t = time.time() - t0
    dashboard.data_bus.push("ch1", float(np.sin(2 * np.pi * t)))
    dashboard.data_bus.push("ch2", float(np.cos(2 * np.pi * t)))
    dashboard.data_bus.push("ch3", float(np.random.normal(0, 1)))

    mode_name = dashboard.window.fullscreen_mode.upper()
    screen_info = f"Screen: {dashboard.window.selected_screen.width}x{dashboard.window.selected_screen.height}"
    dashboard.renderer.draw_text(
        f"Time: {t:.2f}s | Mode: {mode_name} | {screen_info} | ESC: exit fullscreen", 
        20, 20
    )

# Run the dashboard
dashboard.run(signal_source_update=sim_update)