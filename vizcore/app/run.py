# vizcore/app/run.py
import numpy as np
import time
from vizcore.app.dashboard import Dashboard
from vizcore.layout.rect import Rect
from vizcore.widgets.plots.line_plot import LinePlot

dashboard = Dashboard(width=600, height=300, title="Line Plot Test", rows=1, cols=1)
plot = LinePlot(Rect(0, 0, 600, 300), channels=1, buffer_size=256)
dashboard.add_widget(plot, row=0, col=0, signal="ch1")

t0 = time.time()
def sim_update():
    t = time.time() - t0
    dashboard.data_bus.push("ch1", float(np.sin(2 * np.pi * t)))

dashboard.run(signal_source_update=sim_update)