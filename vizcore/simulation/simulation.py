import math

class Signal:
    """A tracked leaf variable with metadata."""
    def __init__(self, default, units=None, description=""):
        self.default = default
        self.units = units
        self.description = description
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None: return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value

class SimNode:
    """A hierarchical branch that automatically packages its Signals and child Nodes."""
    def __init__(self, name):
        self.name = name

    def get_state(self):
        state = {}
        # 1. Introspect for Signals (Leaves)
        for attr_name in dir(self.__class__):
            attr = getattr(self.__class__, attr_name)
            if isinstance(attr, Signal):
                # We could even pass the metadata here if we want the DataBus to know the units!
                state[attr_name] = getattr(self, attr_name)
        
        # 2. Introspect for child SimNodes (Branches)
        for attr_name, attr_val in self.__dict__.items():
            if isinstance(attr_val, SimNode):
                state[attr_name] = attr_val.get_state()
        
        return state


class AttitudeControlSim(SimNode):
    # 1. Declare tracked attributes at the class level using the Signal descriptor.
    eulerian_x = Signal(0.0)
    eulerian_y = Signal(0.0)
    eulerian_z = Signal(0.0)
    velocity = Signal([0.0, 0.0, 0.0])  # A 3D vector for testing signal attachment
    displacement = Signal([0.0, 0.0, 0.0])  # Another vector to test multiple signals
    temperature = Signal(25.0)  # A scalar signal to test mixed types

    def __init__(self):
        super().__init__("AttitudeControl")
        # Private variables that aren't Signals won't be pushed to the visualizer!
        self.time = 0.0
        self._last_log_time = -1.0

    def step(self, dt):
        self.time += dt
        
        # 2. Modify them exactly like ordinary instance variables.
        self.eulerian_x = math.sin(self.time) * 0.5 
        # self.eulerian_y = math.cos(self.time * 0.5) * 0.5
        # self.eulerian_z += dt * 0.2
        
        # The velocity oscillates to create an interesting dynamic arrow
        # self.velocity = [math.sin(self.time) * 2.0, math.cos(self.time) * 2.0, 0.5]
        self.velocity = [1,0,-1]
        
        self.displacement = [math.sin(self.time * 0.5) * 1.0, math.cos(self.time * 0.5) * 1.0, 0.0]

    def push_logs(self, data_bus):
        """
        Push non-Signal log entries directly to DataBus fixed channels.
        This enables LogConsole without requiring Signal descriptors for logs.
        """
        # Throttle log emission to avoid flooding each frame
        curr_bucket = int(self.time * 2.0)  # 2 logs per second max
        if curr_bucket == self._last_log_time:
            return
        self._last_log_time = curr_bucket

        data_bus.push("DEBUG", {
            "message": f"t={self.time:.2f} vel={self.velocity} disp={self.displacement}",
        })

        speed = (self.velocity[0] ** 2 + self.velocity[1] ** 2 + self.velocity[2] ** 2) ** 0.5
        if speed > 2.5:
            data_bus.push("WARN", {"message": f"High speed detected: {speed:.2f}"})

        if any(vel < 0.0 for vel in self.velocity):
            data_bus.push("ERROR", {"message": f"Velocity exceeds safe limits: {self.velocity}"})

        data_bus.push("INFO", {"message": "Simulation tick"})
