"""Manejo de los puertos de sensores del EV3 en modo I2C.

El EV3 solo detecta solo los sensores I2C tipo NXT que estan en la
direccion 0x01. Ni el Arduino Nano (0x08) ni el AbsoluteIMU (0x11) lo
estan, asi que hay que configurar el puerto a mano.
"""

import glob
import os
import time


def buscar_puerto(direccion_puerto):
    """Devuelve la ruta /sys/class/lego-port/portN del puerto pedido.

    `direccion_puerto` es la direccion de ev3dev, por ejemplo
    'ev3-ports:in4'. Se acepta tambien la forma corta 'in4' u 'outD',
    que es la que usan las clases de motores de ev3dev2.
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
    """Fija el modo de un puerto si no lo tiene ya.

    Se usa para los puertos de salida: `dc-motor` para alimentar el Nano
    desde el puerto D, ya que en `auto` el ladrillo no detecta un
    dispositivo pasivo y el puerto queda en estado `error`.
    """
    ruta = buscar_puerto(direccion_puerto)
    if modo_actual(direccion_puerto) != modo:
        _escribir(ruta, 'mode', modo)
        time.sleep(0.5)
    return ruta


def poner_other_i2c(direccion_puerto):
    """Deja el puerto listo para hablar I2C crudo.

    Se usa para el Arduino Nano, que no sigue el protocolo NXT.
    Despues de esto aparece /dev/i2c-inN.
    """
    ruta = buscar_puerto(direccion_puerto)
    if modo_actual(direccion_puerto) != 'other-i2c':
        _escribir(ruta, 'mode', 'other-i2c')
        time.sleep(0.5)
    return ruta


def poner_nxt_i2c(direccion_puerto, driver, direccion_i2c):
    """Carga un driver de ev3dev sobre un sensor I2C en el puerto.

    Equivale a:
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
    """Devuelve el puerto a deteccion automatica."""
    ruta = buscar_puerto(direccion_puerto)
    try:
        _escribir(ruta, 'mode', 'auto')
    except IOError:
        pass
