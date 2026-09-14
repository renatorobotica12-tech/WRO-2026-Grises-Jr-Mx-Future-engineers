"""Numeric helpers shared by the control code."""


def map_range(value, from_low, from_high, to_low, to_high):
    """Rescale a value from one range to another, in floating point.

    Integer implementations of this truncate. This one does not: the EV3
    works in floating point, and truncating here would only add noise to
    the control loop.
    """
    span = from_high - from_low
    if span == 0:
        return to_low
    return (value - from_low) * (to_high - to_low) / span + to_low


def constrain(value, minimum, maximum):
    """Clamp a value between two bounds."""
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def clamp_abs(value, limit):
    """Clamp a value to +-limit."""
    return constrain(value, -limit, limit)
