"""Alimentacion del Arduino Nano desde un puerto de motores del EV3.

El Nano se alimenta del puerto D tratandolo como un motor de corriente
continua. Los datos siguen yendo por USB; esto es solo corriente.

Por que funciona: un puerto de salida del EV3 entrega la tension de la
bateria entre sus pines de potencia. A ciclo de trabajo 100 % la salida
queda continua, no conmutada, que es lo unico que sirve para alimentar
electronica. A menos de 100 % seria una onda cuadrada y el regulador del
Nano lo pasaria mal.

En ev3dev hay que poner el puerto en modo `dc-motor`, porque en `auto` el
ladrillo no detecta nada (un dispositivo pasivo no tiene identificacion) y
el puerto se queda en estado `error`.
"""

import time

from . import config, ports


class AlimentacionNano(object):

    def __init__(self, puerto=None, duty=None):
        self.puerto = puerto or config.ARD_ALIMENTACION_PUERTO
        self.duty = config.ARD_ALIMENTACION_DUTY if duty is None else duty
        self.motor = None

        if not self.puerto:
            return

        from ev3dev2.motor import DcMotor

        ports.poner_modo(self.puerto, 'dc-motor')
        self.motor = DcMotor(self.puerto)

    # ----------------------------------------------------------------

    def encender(self):
        """Da corriente y espera a que el Nano arranque.

        Hay que llamarla ANTES de abrir el puerto serie: si se enciende
        despues, el Nano se reinicia con el serie ya abierto y se pierden
        tramas hasta que vuelve.
        """
        if self.motor is None:
            return

        self.motor.duty_cycle_sp = self.duty
        self.motor.run_forever()
        time.sleep(config.ARD_ALIMENTACION_ESPERA)

    def apagar(self):
        if self.motor is None:
            return
        try:
            self.motor.stop()
        except Exception:
            pass

    @property
    def encendida(self):
        if self.motor is None:
            return False
        return 'running' in self.motor.state
