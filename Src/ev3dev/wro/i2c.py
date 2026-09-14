"""Raw I2C access from ev3dev.

ev3dev exposes /dev/i2c-in1 .. /dev/i2c-in4 for the sensor ports. We use
smbus2 because it is pure Python and accepts a device path:

    sudo pip3 install smbus2
"""

import glob
import os

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:                                  # pragma: no cover
    SMBus = None
    i2c_msg = None


def ruta_bus(direccion_puerto):
    """Turn 'ev3-ports:in4' into '/dev/i2c-in4'."""
    numero = direccion_puerto.split(':in')[-1]
    ruta = '/dev/i2c-in%s' % numero
    if os.path.exists(ruta):
        return ruta
    # Some ev3dev images do not create the symlink; fall back to looking
    # for the real adapter.
    candidatos = sorted(glob.glob('/dev/i2c-*'))
    if candidatos:
        return candidatos[-1]
    raise IOError('no hay bus I2C para %s; revise el modo del puerto'
                  % direccion_puerto)


def abrir(direccion_puerto):
    if SMBus is None:
        raise ImportError('falta smbus2: sudo pip3 install smbus2')
    return SMBus(ruta_bus(direccion_puerto))


def leer_bloque(bus, direccion, cantidad):
    """Plain read of N bytes, with no register write first."""
    mensaje = i2c_msg.read(direccion, cantidad)
    bus.i2c_rdwr(mensaje)
    return list(mensaje)


def escribir_bloque(bus, direccion, datos):
    mensaje = i2c_msg.write(direccion, bytes(bytearray(datos)))
    bus.i2c_rdwr(mensaje)


def leer_registros(bus, direccion, registro, cantidad):
    """Write the register address, then read. Used by mindsensors devices."""
    escritura = i2c_msg.write(direccion, bytes(bytearray([registro])))
    lectura = i2c_msg.read(direccion, cantidad)
    bus.i2c_rdwr(escritura, lectura)
    return list(lectura)
