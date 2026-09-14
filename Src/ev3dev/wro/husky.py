"""HuskyLens camera read through the OFDL adapter.

https://github.com/ofdl-robotics-tw/EV3-HuskyLens-Stuff

The adapter carries an Arduino Pro Mini that translates the HuskyLens
data into the LEGO UART protocol. To the EV3 it looks like an ordinary
sensor, so ev3dev detects it on its own: no port mode to force and no
driver to install, unlike the Nano over I2C.

Measured on the robot: ev3dev sees it as driver `ev3-uart-84`, with
modes `Data-EV3HSK` and `Time-EV3HSK`, and it returns **eight** s32
values, not six.

The real ordering is **not** the one the adapter's own README gives:

    0 X   1 Y   2 W   3 H   4 ID   5 State   6 and 7 unused

This was confirmed by watching index 5: it alternates between 1 and 7,
which are exactly the "object detected" and "sees none" codes, and when
it reads 7 every other value drops to zero.

We read `bin_data` rather than eight separate `value(i)` calls. That is
a single atomic 32-byte read, so data from two different frames can
never be mixed, and it takes 5 ms instead of 49 ms. At 49 ms the camera
alone would hold the control loop down to 20 Hz.

State codes, per the adapter's README:

    9  adapter connected but no HuskyLens attached
    8  connected, but no objects have been learned
    7  connected with learned objects, but seeing none right now
    1  an object is detected
    0  port disconnected, or data lost
"""

import glob
import struct
import time

from ev3dev2.sensor import Sensor

from . import config
from .util import constrain, map_range

ESTADO_OBJETO = 1
ESTADO_SIN_DETECCION = 7
ESTADO_SIN_APRENDIZAJE = 8
ESTADO_SIN_CAMARA = 9
ESTADO_SIN_PUERTO = 0


class HuskyLens(object):

    def __init__(self, direccion_puerto=None):
        direccion_puerto = direccion_puerto or config.PUERTO_HUSKY
        self.sensor = Sensor(direccion_puerto)

        if config.HUSKY_MODO in self.sensor.modes:
            self.sensor.mode = config.HUSKY_MODO
        else:
            self.sensor.mode = self.sensor.modes[0]

        self.ruta = self._buscar_sysfs(direccion_puerto)
        self.formato = '<%di' % self.sensor.num_values
        self.bytes = 4 * self.sensor.num_values

        self.estado = ESTADO_SIN_PUERTO
        self.id = 0
        self.x = 0.0                 # centred on 0, negative to the left
        self.y = 0.0
        self.ancho = 0
        self.alto = 0

        # Hold-over state. See angulo_esquive_retenido().
        self.reteniendo = False      # telemetry only
        self._id_enganchado = None
        self._ancho_enganchado = 0
        self._ultimo_angulo = None
        self._marca_angulo = 0.0

    # ----------------------------------------------------------------

    @staticmethod
    def _buscar_sysfs(direccion_puerto):
        for ruta in glob.glob('/sys/class/lego-sensor/sensor*'):
            with open(ruta + '/address') as f:
                if f.read().strip().startswith(direccion_puerto):
                    return ruta
        raise IOError('no se encontro la HuskyLens en %s' % direccion_puerto)

    def leer_crudo(self):
        """All eight values in one atomic read of bin_data."""
        with open(self.ruta + '/bin_data', 'rb') as f:
            return struct.unpack(self.formato, f.read(self.bytes))

    def actualizar(self):
        """Read one frame. Returns True if an object is detected."""
        valores = self.leer_crudo()
        self.estado = valores[config.HUSKY_IDX_STATE]

        if self.estado != ESTADO_OBJETO:
            self.id = 0
            self.x = self.y = 0.0
            self.ancho = self.alto = 0
            return False

        self.id = valores[config.HUSKY_IDX_ID]
        self.x = valores[config.HUSKY_IDX_X] - config.HUSKY_CENTRO_X
        self.y = valores[config.HUSKY_IDX_Y] - config.HUSKY_CENTRO_Y

        # Axis inversion happens here, on the already-centred coordinate,
        # and not further down the chain. That way everything downstream
        # -- targets, per-colour clamps, the steering sign -- keeps the
        # same meaning with any lens. Swapping the lens should not force
        # a retune of the rest.
        if config.HUSKY_INVERTIR_X:
            self.x = -self.x
        if config.HUSKY_INVERTIR_Y:
            self.y = -self.y

        self.ancho = valores[config.HUSKY_IDX_W]
        self.alto = valores[config.HUSKY_IDX_H]
        return True

    @property
    def color(self):
        """Name of the colour seen, for telemetry."""
        if self.id == config.HUSKY_ID_VERDE:
            return 'VERDE'
        if self.id == config.HUSKY_ID_ROJO:
            return 'ROJO '
        return 'id=%-2d' % self.id

    @property
    def hay_objeto(self):
        return self.estado == ESTADO_OBJETO and self.id > 0

    def diagnostico(self):
        return {
            ESTADO_SIN_PUERTO: 'puerto desconectado o datos perdidos',
            ESTADO_OBJETO: 'objeto detectado',
            ESTADO_SIN_DETECCION: 'conectada, no ve ningun objeto aprendido',
            ESTADO_SIN_APRENDIZAJE: 'conectada, sin objetos aprendidos',
            ESTADO_SIN_CAMARA: 'adaptador si, HuskyLens no',
        }.get(self.estado, 'estado desconocido %s' % self.estado)

    # ----------------------------------------------------------------

    def angulo_esquive(self):
        """Steering angle to avoid the block currently in view.

        A proportional controller on the block's position in the image.
        The error is how far the block still is from its target, and the
        steering corrects until that error is gone:

            error = X - target
            angle = constrain(map(error, -160,160, -limit,+limit), lo, hi)

        The target comes from config, per colour, and it is THE knob for
        how wide the detour around a block is. Which sign goes with which
        side was settled by testing on track, not by reasoning: the first
        reasoned version sent the robot past each block on the wrong side.

        Note the target must stay inside +-HUSKY_CENTRO_X. A target
        outside the image is a position the block can never reach, so the
        error never crosses zero and the steering never straightens out
        while the block is in view.

        Returns None if the ID in view is neither of the two configured
        colours.
        """
        target = self.target()
        if target is None:
            return None

        recorte = (config.HUSKY_LIMITE_VERDE
                   if self.id == config.HUSKY_ID_VERDE
                   else config.HUSKY_LIMITE_ROJO)

        # The clamps are fractions of the steering limit, not degrees.
        minimo = recorte[0] * config.VOLANTE_LIMITE
        maximo = recorte[1] * config.VOLANTE_LIMITE

        angulo = map_range(self.x - target,
                           -config.HUSKY_CENTRO_X, config.HUSKY_CENTRO_X,
                           -config.VOLANTE_LIMITE, config.VOLANTE_LIMITE)
        return constrain(angulo, minimo, maximo)

    def angulo_esquive_retenido(self):
        """angulo_esquive() that rides out short camera dropouts.

        Same three-state pattern that `_filtrar()` applies to the
        ultrasonic readings in ultrasonics.py, and for the same reason: a
        single failed frame does not mean the block is gone.

            good reading  -> use it and remember it
            short dropout -> hold the last good command
            long dropout  -> hand control back to wall following

        Without this, every one-frame dropout handed control back to the
        wall follower, which at that instant saw a large error and slammed
        the steering to full lock. Measured: +1.9 degrees to +50.6 and
        back inside 300 ms, with the block in view the whole time.

        It also latches onto one block. With two in view the OFDL adapter
        does not keep returning the same bounding box: it switches between
        them, and without latching the robot gets commands for opposite
        sides on consecutive loops. Measured: id=1 asking for +50.6
        (right) and 300 ms later id=2 asking for -27.2 (left).

        Control only moves to a different block when the new one looks
        clearly WIDER, by HUSKY_MARGEN_ANCHO. Width is the only proximity
        information available: the pillars are all identical, so wider
        means closer, and the closest one is the urgent one. This
        recovers the "widest box wins" rule by comparing across reads
        instead of within a single one.

        A time window does NOT solve the switching. Stretching it from
        0.1 to 0.3 s left the behaviour unchanged, because the switching
        happens on longer timescales than any reasonable window; all the
        longer window added was staleness.

        Returns None when there is genuinely nothing to avoid, same as
        angulo_esquive(), which is left untouched so `check_hw.py husky`
        can still show the raw, unfiltered angle.
        """
        ahora = time.time()
        vigente = (self._ultimo_angulo is not None
                   and ahora - self._marca_angulo <= config.HUSKY_RETENCION)

        if self.hay_objeto:
            # A different block while the latched one is still current:
            # only yield control if it is closer than the one being
            # avoided right now.
            if (vigente
                    and self.id != self._id_enganchado
                    and self.ancho < (self._ancho_enganchado
                                      * config.HUSKY_MARGEN_ANCHO)):
                self.reteniendo = True
                return self._ultimo_angulo

            angulo = self.angulo_esquive()
            if angulo is not None:
                self._id_enganchado = self.id
                self._ancho_enganchado = self.ancho
                self._ultimo_angulo = angulo
                self._marca_angulo = ahora
                self.reteniendo = False
                return angulo

        if vigente:
            self.reteniendo = True
            return self._ultimo_angulo

        self._id_enganchado = None
        self._ancho_enganchado = 0
        self._ultimo_angulo = None
        self.reteniendo = False
        return None

    def target(self):
        """Where the block should end up in the image, by colour.

        None if the ID in view is neither of the two configured colours.
        """
        if self.id == config.HUSKY_ID_VERDE:
            return config.HUSKY_TARGET_VERDE
        if self.id == config.HUSKY_ID_ROJO:
            return config.HUSKY_TARGET_ROJO
        return None
