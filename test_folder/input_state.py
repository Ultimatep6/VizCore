from dataclasses import dataclass


@dataclass
class InputState:
    x: float = 0.0
    y: float = 0.0
    ctrl_pressed: bool = False
    dragging_border: bool = False
