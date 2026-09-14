"""Powering the Arduino Nano from one of the EV3 motor ports.

The Nano draws its power from port D, driven as if it were a DC motor.
Data still travels over USB; this is current only.

Why it works: an EV3 output port puts the battery voltage across its
power pins. At 100 % duty cycle the output is continuous rather than
switched, which is the only form that is usable for powering
electronics. Below 100 % it would be a square wave and the Nano's
regulator would struggle with it.

The port has to be forced into `dc-motor` mode. In `auto` the brick
detects nothing, because a passive device has no identification, and the
port is left in the `error` state.
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
        """Apply power and wait for the Nano to boot.

        Must be called BEFORE opening the serial port. Powering up
        afterwards restarts the Nano with the serial link already open,
        and frames are lost until it comes back.
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
