"""Utilidades numericas equivalentes a las de Arduino / Mind+."""


def map_range(value, from_low, from_high, to_low, to_high):
    """Equivalente exacto de map() de Arduino, pero en punto flotante.

    Arduino usa enteros y trunca; aqui no se trunca porque el EV3 trabaja
    con flotantes y truncar solo agrega ruido al control.
    """
    span = from_high - from_low
    if span == 0:
        return to_low
    return (value - from_low) * (to_high - to_low) / span + to_low


def constrain(value, minimum, maximum):
    """Equivalente de constrain() de Arduino."""
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def clamp_abs(value, limit):
    """Limita el valor a +-limit."""
    return constrain(value, -limit, limit)
