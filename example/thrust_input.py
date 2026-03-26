from vizcore.app.dashboard import Dashboard
from vizcore.widgets.indicators.bar_meter import BarMeter
import time
import numpy as np

def sim(ta, te, dt):
    """Generator that yields time values from ta to te."""
    t = time.time()
    while t < te:
        yield t - ta
        time.sleep(dt)  # Control simulation speed
        t = time.time()


if __name__ == "__main__":
    # Simulation parameters
    ta = time.time()
    te = ta + 10  # Run for 10 seconds
    dt = 0.05  # 50ms update interval (20 Hz)

    # Create dashboard
    dashboard = Dashboard(
        title="Parabolic Motion", 
        rows=2, 
        cols=2, 
        fullscreen=True, 
        fullscreen_mode="maximized"
    )
    
    # Create bar meters
    throttle_bar = BarMeter(v_max=10, v_min=0, orientation='vertical', title='Throttle')
    altitude_bar = BarMeter(v_max=100, v_min=0, orientation='vertical', title='Altitude')
    velocity_bar = BarMeter(v_max=50, v_min=-50, orientation='horizontal', title='Velocity')
    
    # Add widgets to dashboard
    dashboard.add_widget(throttle_bar, row=0, col=0, signal='throttle')
    dashboard.add_widget(altitude_bar, row=0, col=1, signal='altitude')
    dashboard.add_widget(velocity_bar, row=1, col=0, signal='velocity')
    
    # Create simulation iterator
    sim_iter = sim(ta=ta, te=te, dt=dt)

    def sim_update():
        """Update simulation state each frame."""
        try:
            t = next(sim_iter)
            
            # Simulate some physics
            # Throttle varies sinusoidally
            throttle = 5 + 5 * np.sin(2 * np.pi * t / 5)
            
            # Altitude follows a parabolic trajectory
            altitude = -5 * (t - 5)**2 + 125
            altitude = max(0, altitude)  # Can't go below ground
            
            # Velocity is derivative of altitude
            velocity = -10 * (t - 5)
            
            # Push to data bus
            dashboard.data_bus.push("throttle", throttle)
            dashboard.data_bus.push("altitude", altitude)
            dashboard.data_bus.push("velocity", velocity)
            
        except StopIteration:
            print("Simulation complete!")
            dashboard.close()
    
    # Run the dashboard
    dashboard.run(signal_source_update=sim_update)