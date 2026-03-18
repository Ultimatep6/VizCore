# vizcore/app/run.py
import numpy as np
import time
from vizcore.app.dashboard import Dashboard
from vizcore.layout.rect import Rect
from vizcore.widgets.plots.line_plot import LinePlot

# dashboard = Dashboard(fullscreen=True, title="Test", rows=2, cols=2)
# plot1 = LinePlot(title="This Title Should Be Visible Now")
# dashboard.add_widget(plot1, row=0, col=0, signal="test")
# dashboard.run(signal_source_update=lambda: dashboard.data_bus.push("test", np.random.normal(0, 1)))

dashboard = Dashboard(title="Line Plot Test", rows=2, cols=2, fullscreen=True)


plot1 = LinePlot(channels=1, buffer_size=256, margin=50, title="sin")
plot2 = LinePlot(channels=1, buffer_size=256, margin=50, title="cos")
plot3 = LinePlot(channels=1, buffer_size=256, margin=50, title="noise")

dashboard.add_widget(plot1, row=0, col=0, signal="ch1")
dashboard.add_widget(plot2, row=0, col=1, signal="ch2")
dashboard.add_widget(plot3, row=1, col=0, signal="ch3")


t0 = time.time()
def sim_update():
    t = time.time() - t0
    dashboard.data_bus.push("ch1", float(np.sin(2 * np.pi * t)))
    dashboard.data_bus.push("ch2", float(np.cos(2 * np.pi * t)))
    dashboard.data_bus.push("ch3", float(np.random.normal(0, 1)))

    dashboard.renderer.draw_text(f"Time: {t:.2f}s", 20, 20)

dashboard.run(signal_source_update=sim_update)