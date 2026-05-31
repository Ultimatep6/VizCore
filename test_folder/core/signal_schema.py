from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


class V:
    @staticmethod
    def normalized(tol=1e-6):
        return lambda v: abs(np.linalg.norm(v) - 1.0) < tol

    @staticmethod
    def positive():
        return lambda x: x > 0

    @staticmethod
    def negative():
        return lambda x: x < 0

    @staticmethod
    def non_zero():
        return lambda x: x != 0

    @staticmethod
    def in_range(low, high):
        return lambda x: (low <= x) & (x <= high)

    @staticmethod
    def non_negative():
        return lambda x: x >= 0


@dataclass
class SignalSchema:
    shape: Optional[tuple] = None
    dtype: Optional[type] = None
    constraints: Optional[dict] = None
    validators: Optional[dict[str, callable]] = None
    units: str = ""
    description: str = ""

    def matches(self, other: SignalSchema) -> bool:
        if self.shape is not None and other.shape is not None:
            if self.shape != other.shape:
                return False
        if self.dtype is not None and other.dtype is not None:
            if self.dtype != other.dtype:
                return False
        if self.constraints:
            if other.constraints is None:
                return False
            for key, value in self.constraints.items():
                if key not in other.constraints or other.constraints[key] != value:
                    return False
        if self.validators:
            if other.constraints is None:
                return False
            for key in self.validators:
                if key not in other.constraints:
                    return False
        return True

    def validate(self, value) -> tuple[bool, list[str]]:
        if not self.validators:
            return True, []
        errors = []
        for key, fn in self.validators.items():
            try:
                result = fn(value)
                if isinstance(result, np.ndarray):
                    result = bool(result.all())
                if not result:
                    errors.append(f"Validator '{key}' rejected value {value}")
            except Exception as e:
                errors.append(f"Validator '{key}' raised: {e}")
        return len(errors) == 0, errors

    def to_dict(self) -> dict:
        return {
            "shape": self.shape,
            "dtype": self.dtype,
            "constraints": self.constraints,
            "units": self.units,
            "description": self.description,
        }

    @classmethod
    def infer_from_value(cls, value, units="", description="") -> SignalSchema:
        shape = None
        dtype = None
        if isinstance(value, np.ndarray):
            shape = value.shape
            dtype = value.dtype
        elif isinstance(value, (list, tuple)):
            shape = (len(value),)
            dtype = type(value[0]) if value else None
        else:
            shape = (1,)
            dtype = type(value)
        return cls(shape=shape, dtype=dtype, units=units, description=description)
