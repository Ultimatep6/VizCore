import math
import numpy as np
from core.signal_schema import SignalSchema


class Signal:
    def __init__(self, default, units=None, description="", schema=None):
        self.default = default
        self.units = units
        self.description = description
        self.name = None
        if schema is not None:
            self.schema = schema
        else:
            self.schema = SignalSchema.infer_from_value(
                default, units=units or "", description=description or ""
            )

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, self.default)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value


class SimNode:
    def __init__(self, name):
        self.name = name
        self.get_signal_schemas = lambda cls=self, prefix="": get_signal_schemas(
            cls, prefix
        )
        self.get_state = lambda cls=self: get_state(cls)


class SimContainer:
    def __init__(self) -> None:

        self.get_signal_schemas = lambda cls=self, prefix="": get_signal_schemas(
            cls, prefix
        )
        self.get_value_at = lambda path, cls=self: get_value_at(cls, path)
        self.get_state = lambda cls=self: get_state(cls)

    def step(self, dt):
        raise NotImplemented


def get_signal_schemas(cls, prefix=""):
    schemas = {}
    for attr_name in dir(cls.__class__):
        attr = getattr(cls.__class__, attr_name)
        if isinstance(attr, Signal):
            path = f"{prefix}.{attr_name}" if prefix != "" else attr_name
            schemas[path] = attr.schema

    for attr_name, attr_val in cls.__dict__.items():
        if isinstance(attr_val, (SimNode, SimContainer)):
            sub_prefix = f"{prefix}.{attr_name}" if prefix != "" else attr_name
            schemas.update(get_signal_schemas(cls=attr_val, prefix=sub_prefix))
        elif isinstance(attr_val, (list, tuple)):
            for idx, item in enumerate(attr_val):
                if isinstance(item, (SimNode, SimContainer)):
                    sub_prefix = f"{prefix}.{attr_name}.{idx}"
                    if prefix == "":
                        sub_prefix = f"{attr_name}.{idx}"
                    schemas.update(get_signal_schemas(cls=item, prefix=sub_prefix))
    return schemas


def get_value_at(cls, path):
    parts = path.split(".")
    obj = cls
    for part in parts:
        if not part:
            continue
        if isinstance(obj, (list, tuple)):
            obj = obj[int(part)]
        else:
            obj = getattr(obj, part)
    return obj


def get_state(obj):
    state = {}
    for attr_name in dir(obj.__class__):
        attr = getattr(obj.__class__, attr_name)
        if isinstance(attr, Signal):
            state[attr_name] = getattr(obj, attr_name)
    for attr_name, attr_val in obj.__dict__.items():
        if isinstance(attr_val, (SimNode, SimContainer)):
            state[attr_name] = attr_val.get_state()
        elif isinstance(attr_val, (list, tuple)):
            state[attr_name] = [
                item.get_state() if isinstance(item, (SimNode, SimContainer)) else item
                for item in attr_val
            ]
    return state


class AttitudeControlSim(SimNode):
    eulerian_x = Signal(0.0)
    eulerian_y = Signal(0.0)
    eulerian_z = Signal(0.0)
    velocity = Signal([0.0, 0.0, 0.0])
    displacement = Signal([0.0, 0.0, 0.0])
    temperature = Signal(25.0)

    def __init__(self):
        super().__init__("AttitudeControl")
        self.time = 0.0
        self._last_log_time = -1.0

    def step(self, dt):
        self.time += dt
        self.eulerian_x = math.sin(self.time) * 0.5
        self.velocity = [1, 0, -1]
        self.displacement = [
            math.sin(self.time * 0.5) * 1.0,
            math.cos(self.time * 0.5) * 1.0,
            0.0,
        ]

    def push_logs(self, data_bus):
        curr_bucket = int(self.time * 2.0)
        if curr_bucket == self._last_log_time:
            return
        self._last_log_time = curr_bucket
        data_bus.push(
            "DEBUG",
            {
                "message": f"t={self.time:.2f} vel={self.velocity} disp={self.displacement}",
            },
        )
        speed = (
            self.velocity[0] ** 2 + self.velocity[1] ** 2 + self.velocity[2] ** 2
        ) ** 0.5
        if speed > 2.5:
            data_bus.push("WARN", {"message": f"High speed detected: {speed:.2f}"})
        if any(vel < 0.0 for vel in self.velocity):
            data_bus.push(
                "ERROR",
                {
                    "message": f"Velocity exceeds safe limits: {self.velocity}",
                },
            )
        data_bus.push("INFO", {"message": "Simulation tick"})
