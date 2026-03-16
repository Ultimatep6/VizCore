# vizcore/app/run.py
import numpy as np
import time
from vizcore.app.dashboard import Dashboard
from vizcore.layout.rect import Rect
from vizcore.widgets.plots.line_plot import LinePlot

dashboard = Dashboard(width=1200, height=300, title="Line Plot Test", rows=1, cols=2)

plot1 = LinePlot(Rect(0, 0, 600, 300), channels=1, buffer_size=256,margin=50)
plot2 = LinePlot(Rect(600, 0, 600, 300), channels=1, buffer_size=256,margin=50)
dashboard.add_widget(plot1, row=0, col=0, signal="ch1")
dashboard.add_widget(plot2, row=0, col=1, signal="ch2")

t0 = time.time()
def sim_update():
    t = time.time() - t0
    dashboard.data_bus.push("ch1", float(np.sin(2 * np.pi * t)))
    dashboard.data_bus.push("ch2", float(np.cos(2 * np.pi * t)))

dashboard.run(signal_source_update=sim_update)