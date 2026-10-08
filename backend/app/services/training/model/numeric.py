"""Small numeric helpers shared by the model (pure, no parameters)."""

import math


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    """0 below edge0, 1 above edge1, C1-smooth in between."""
    if edge1 <= edge0:
        return 1.0 if x >= edge1 else 0.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def round_half_up(value: float) -> int:
    """Round to the nearest integer, halves up (no banker's rounding)."""
    return int(math.floor(value + 0.5))
