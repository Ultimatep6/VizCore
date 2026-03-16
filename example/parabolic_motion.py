from vizcore.app.dashboard import Dashboard
from vizcore.widgets.plots.line_plot import LinePlot

def make_sim(h0, vx0, vy0, dt=0.05, g=9.81, drag_x=0.01, drag_y=0.01):
    """Generator that yields one simulation step at a time with separate horizontal and vertical drag."""
    t = 0.0
    x = 0.0
    y = h0
    vx = vx0
    vy = vy0
    while True:
        # Apply horizontal drag
        vx -= drag_x * vx * dt
        # Apply vertical drag and gravity
        vy -= (g + drag_y * vy) * dt
        x += vx * dt
        y += vy * dt
        yield t, x, y, vy
        t += dt
        if y < 0:
            t = 0.0
            x = 0.0
            y = h0
            vx = vx0
            vy = vy0

if __name__ == "__main__":
    dashboard = Dashboard(title="Parabolic Motion", rows=2, cols=2, fullscreen=True)
    dashboard.add_widget(LinePlot(channels=1, buffer_size=512, margin=50), row=0, col=0, signal="vx")
    dashboard.add_widget(LinePlot(channels=1, buffer_size=512, margin=50), row=0, col=1, signal="vy")
    dashboard.add_widget(LinePlot(channels=1, buffer_size=512, margin=50), row=1, col=0, signal="y")
    dashboard.add_widget(LinePlot(channels=1, buffer_size=512, margin=50), row=1, col=1, signal="x")

    sim = make_sim(h0=1000, vx0=5, vy0=10,drag_x=0.0)

    def sim_update():
        t, x, y, vy = next(sim)
        dashboard.data_bus.push("vx", 5.0)   # constant
        dashboard.data_bus.push("vy", vy)
        dashboard.data_bus.push("x", x)
        dashboard.data_bus.push("y", y)

    dashboard.run(signal_source_update=sim_update)