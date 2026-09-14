"""Driving the EV3 sensor ports in I2C mode.

The EV3 only auto-detects NXT-style I2C sensors that sit at address
0x01. Neither the Arduino Nano (0x08) nor the AbsoluteIMU (0x11) does,
so the port has to be configured by hand.
"""

import glob
import os
import time


def buscar_puerto(direccion_puerto):
    """Return the /sys/class/lego-port/portN path for a port.

    `direccion_puerto` is the ev3dev address, for example
    'ev3-ports:in4'. The short forms 'in4' and 'outD' are also accepted,
    since those are what the ev3dev2 motor classes use.
    """
    if not direccion_puerto.startswith('ev3-ports:'):
        direccion_puerto = 'ev3-ports:' + direccion_puerto

    for ruta in glob.glob('/sys/class/lego-port/port*'):
        try:
            with open(os.path.join(ruta, 'address')) as f:
                if f.read().strip() == direccion_puerto:
                    return ruta
        except IOError:
            continue
    raise IOError('no se encontro el puerto %s' % direccion_puerto)


def _escribir(ruta, archivo, texto):
    with open(os.path.join(ruta, archivo), 'w') as f:
        f.write(texto)


def modo_actual(direccion_puerto):
    ruta = buscar_puerto(direccion_puerto)
    with open(os.path.join(ruta, 'mode')) as f:
        return f.read().strip()


def poner_modo(direccion_puerto, modo):
    """Set a port's mode if it is not already in it.

    Used for the output ports: `dc-motor` to power the Nano from port D,
    since in `auto` the brick does not detect a passive device and the
    port ends up in the `error` state.
    """
    ruta = buscar_puerto(direccion_puerto)
    if modo_actual(direccion_puerto) != modo:
        _escribir(ruta, 'mode', modo)
        time.sleep(0.5)
    return ruta


def poner_other_i2c(direccion_puerto):
    """Put a port into raw I2C mode.

    Used for the Arduino Nano, which does not follow the NXT protocol.
    After this, /dev/i2c-inN appears.
    """
    ruta = buscar_puerto(direccion_puerto)
    if modo_actual(direccion_puerto) != 'other-i2c':
        _escribir(ruta, 'mode', 'other-i2c')
        time.sleep(0.5)
    return ruta


def poner_nxt_i2c(direccion_puerto, driver, direccion_i2c):
    """Load an ev3dev driver onto an I2C sensor on a port.

    Equivalent to:
        echo nxt-i2c > .../mode
        echo "ms-absolute-imu 0x11" > .../set_device
    """
    ruta = buscar_puerto(direccion_puerto)
    if modo_actual(direccion_puerto) != 'nxt-i2c':
        _escribir(ruta, 'mode', 'nxt-i2c')
        time.sleep(0.5)
    _escribir(ruta, 'set_device', '%s 0x%02x' % (driver, direccion_i2c))
    time.sleep(0.5)
    return ruta


def liberar(direccion_puerto):
    """Return a port to automatic detection."""
    ruta = buscar_puerto(direccion_puerto)
    try:
        _escribir(ruta, 'mode', 'auto')
    except IOError:
        pass
