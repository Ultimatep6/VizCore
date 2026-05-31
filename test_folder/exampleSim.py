import math
import numpy as np
from core.simulation import SimContainer, SimNode, Signal


class Particle(SimNode):
    position = Signal([0.0, 0.0, 0.0])

    def __init__(self, name, orbit_radius, speed, phase, z_amp, y_amp):
        super().__init__(name)
        self.orbit_radius = orbit_radius
        self.speed = speed
        self.phase = phase
        self.z_amp = z_amp
        self.y_amp = y_amp
        self._t = 0.0

    def step(self, dt):
        self._t += dt
        t = self._t
        r = self.orbit_radius
        self.position = [
            r * math.cos(t * self.speed + self.phase),
            self.y_amp * math.sin(t * self.speed * 0.7 + self.phase * 1.3),
            self.z_amp * math.sin(t * self.speed * 1.1 + self.phase * 0.5),
        ]


class StaticNode(SimNode):
    position = Signal([0.0, 0.0, 0.0])

    def __init__(self, name, pos):
        super().__init__(name)
        self.position = pos


class ExampleSim(SimContainer):
    def __init__(self):
        super().__init__()
        self.static_nodes = [
            StaticNode("static_0", [2.0, 0.0, 0.0]),
            StaticNode("static_1", [0.0, 2.0, 0.0]),
            StaticNode("static_2", [-1.0, -1.0, 1.0]),
        ]

    def step(self, dt):
        pass

    def run(self):
        pass
