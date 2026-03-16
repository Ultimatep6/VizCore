
from vizcore.app.dashboard import Dashboard
from vizcore.layout.rect import Rect
from vizcore.widgets.plots.line_plot import LinePlot
import pyglet
import time
import numpy as np

if __name__ == "__main__":
    dashboard = Dashboard(width=600, height=300, title="Line Plot Test", rows=1, cols=1)
    rect = Rect(50, 50, 500, 200)
    widget = LinePlot(rect, channels=1, buffer_size=128)
    dashboard.add_widget(widget, row=0, col=0, signal="ch1")

    # Register single signal in the data bus
    dashboard.data_bus.register_signal("ch1")

    start_time = time.time()

    def update(dt):
        t = time.time() - start_time
        value = np.sin(t)
        dashboard.data_bus.push("ch1", value)
        for w in dashboard.widgets:
            w.update(None)
        dashboard.window.clear()
        dashboard.renderer.begin_frame()
        for w in dashboard.widgets:
            w.draw(dashboard.renderer)
        dashboard.renderer.end_frame()
        if time.time() - start_time > 10:
            pyglet.app.exit()

    pyglet.clock.schedule_interval(update, 1/30)
    pyglet.app.run()
