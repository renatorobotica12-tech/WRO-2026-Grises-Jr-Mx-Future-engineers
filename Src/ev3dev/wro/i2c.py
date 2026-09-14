"""Acceso I2C crudo desde ev3dev.

ev3dev crea /dev/i2c-in1 .. /dev/i2c-in4 para los puertos de sensores.
Se usa smbus2 porque es Python puro y acepta una ruta de dispositivo:

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
    """Convierte 'ev3-ports:in4' en '/dev/i2c-in4'."""
    numero = direccion_puerto.split(':in')[-1]
    ruta = '/dev/i2c-in%s' % numero
    if os.path.exists(ruta):
        return ruta
    # Algunas imagenes no crean el enlace; se busca el adaptador real.
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
    """Lectura simple de N bytes, sin registro previo."""
    mensaje = i2c_msg.read(direccion, cantidad)
    bus.i2c_rdwr(mensaje)
    return list(mensaje)


def escribir_bloque(bus, direccion, datos):
    mensaje = i2c_msg.write(direccion, bytes(bytearray(datos)))
    bus.i2c_rdwr(mensaje)


def leer_registros(bus, direccion, registro, cantidad):
    """Escribe el registro y despues lee; lo usan los sensores mindsensors."""
    escritura = i2c_msg.write(direccion, bytes(bytearray([registro])))
    lectura = i2c_msg.read(direccion, cantidad)
    bus.i2c_rdwr(escritura, lectura)
    return list(lectura)
