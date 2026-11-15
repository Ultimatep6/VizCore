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
        ]
        self.particles = [
            Particle("particle_0", 8.0, 0.8, 0.0, 0.5, 0.3),
            Particle("particle_1", 7.0, 0.5, 1.2, 0.8, 0.6),
        ]
        self.get_state = self._get_state

    def _get_state(self):
        state = {
            "static_nodes": [node.get_state() for node in self.static_nodes],
            "particles": [p.get_state() for p in self.particles],
        }
        for i, node in enumerate(self.static_nodes):
            pos = node.position
            state[f"static_node_{i}_x"] = pos[0]
            state[f"static_node_{i}_y"] = pos[1]
            state[f"static_node_{i}_z"] = pos[2]
        for i, p in enumerate(self.particles):
            pos = p.position
            state[f"particle_{i}_x"] = pos[0]
            state[f"particle_{i}_y"] = pos[1]
            state[f"particle_{i}_z"] = pos[2]
        return state

    def step(self, dt):
        for p in self.particles:
            p.step(dt)

    def run(self):
        pass
