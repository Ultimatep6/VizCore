import math

class Signal:
    """Descriptor that flags a variable to automatically be tracked and pushed to the DataBus."""
    def __init__(self, default=0.0):
        self.default = default
        self.name = None

    def __set_name__(self, owner, name):
        # Automatically captures the name of the variable it was assigned to!
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value


class BaseSimulation:
    def __init__(self):
        pass

    @property
    def exposed_signals(self):
        # Automatically detects all attributes using the Signal descriptor
        signals = []
        for name in dir(self.__class__):
            if isinstance(getattr(self.__class__, name, None), Signal):
                signals.append(name)
        return signals

    def step(self, dt):
        pass

    def get_state(self):
        # Automatically packages the state based on detected signals
        return {name: getattr(self, name) for name in self.exposed_signals}


class AttitudeControlSim(BaseSimulation):
    # 1. Declare tracked attributes at the class level using the Signal descriptor.
    eulerian_x = Signal(0.0)
    eulerian_y = Signal(0.0)
    eulerian_z = Signal(0.0)
    velocity = Signal([0.0, 0.0, 0.0])  # A 3D vector for testing signal attachment
    displacement = Signal([0.0, 0.0, 0.0])  # Another vector to test multiple signals
    temperature = Signal(25.0)  # A scalar signal to test mixed types

    def __init__(self):
        super().__init__()
        # Private variables that aren't Signals won't be pushed to the visualizer!
        self.time = 0.0

    def step(self, dt):
        self.time += dt
        
        # 2. Modify them exactly like ordinary instance variables.
        self.eulerian_x = math.sin(self.time) * 0.5 
        self.eulerian_y = math.cos(self.time * 0.5) * 0.5
        self.eulerian_z += dt * 0.2
        
        # The velocity oscillates to create an interesting dynamic arrow
        self.velocity = [math.sin(self.time) * 2.0, math.cos(self.time) * 2.0, 0.5]
        self.displacement = [math.sin(self.time * 0.5) * 1.0, math.cos(self.time * 0.5) * 1.0, 0.0]
