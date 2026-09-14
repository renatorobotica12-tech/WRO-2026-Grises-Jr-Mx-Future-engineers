"""Gyroscope: the AbsoluteIMU read through ev3dev.

The sensor reports angular velocity. The heading angle is obtained by
integrating that velocity against real elapsed time, which is what
docs/BLOQUE_GIRO_ABSOLUTEIMU_EV3.md describes.

This module owns everything to do with heading: calibrating the zero,
integrating, applying the dead band, and deciding when a turn counts as
a track corner.
"""

import time

from . import config, i2c, ports

# Register map of the mindsensors AbsoluteIMU-ACG.
# Check this against the datasheet before trusting the 'raw' backend.
REG_COMANDO = 0x41
REG_GIRO_X = 0x53                   # 6 bytes: X, Y, Z as 16-bit little endian


class _LectorDriver(object):
    """Uses the ev3dev ms-absolute-imu driver.

    On this robot ev3dev detects the AbsoluteIMU on its own, with the
    port left in `auto`, and exposes it as `ev3-ports:in2:i2c17`
    (17 = 0x11). That is why we try to use it as-is first: forcing the
    port mode when it already works would disconnect it and require a
    reboot.

    The manual path stays as a fallback in case it ever stops being
    detected.
    """

    def __init__(self):
        from ev3dev2.sensor import Sensor

        try:
            self.sensor = Sensor(config.PUERTO_IMU)
            if self.sensor.driver_name != config.IMU_DRIVER:
                raise ValueError('driver inesperado: %s'
                                 % self.sensor.driver_name)
        except Exception:
            ports.poner_nxt_i2c(config.PUERTO_IMU, config.IMU_DRIVER,
                                config.IMU_DIRECCION)
            self.sensor = Sensor(config.PUERTO_IMU)

        # It starts up in COMPASS mode; it has to be switched to GYRO
        # explicitly.
        self.sensor.mode = config.IMU_MODO

    def crudo(self):
        return self.sensor.value(config.IMU_EJE)

    def crudo_todos(self):
        """All three axes. Used by the diagnostics to work out which axis
        is the vertical one on this build."""
        return [self.sensor.value(i) for i in range(3)]


class _LectorRaw(object):
    """Reads the gyro registers over direct I2C."""

    def __init__(self):
        ports.poner_other_i2c(config.PUERTO_IMU)
        self.bus = i2c.abrir(config.PUERTO_IMU)
        self.direccion = config.IMU_DIRECCION

    def crudo(self):
        return self.crudo_todos()[config.IMU_EJE]

    def crudo_todos(self):
        datos = i2c.leer_registros(self.bus, self.direccion, REG_GIRO_X, 6)
        ejes = []
        for eje in range(3):
            valor = datos[eje * 2] | (datos[eje * 2 + 1] << 8)
            if valor >= 0x8000:
                valor -= 0x10000
            ejes.append(valor)
        return ejes


class Giroscopio(object):
    """Calibrated angular velocity and accumulated angle of one axis."""

    def __init__(self, backend=None, escala=None):
        backend = backend or config.IMU_BACKEND
        self.escala = config.IMU_ESCALA if escala is None else escala
        self.lector = _LectorDriver() if backend == 'driver' else _LectorRaw()

        self.offset = 0.0
        self.grados = 0.0
        self.velocidad = 0.0
        self._ultimo = time.time()

        # Corner counting. See es_esquina().
        self.esquinas_descartadas = 0
        self._ultima_esquina = 0.0

    # ----------------------------------------------------------------

    def calibrar(self, muestras=None, mostrar=None):
        """Average the zero offset with the robot standing still.

        If the robot moves during this call, corner counting is wrong for
        the whole run: the offset error integrates into a steady drift of
        the heading angle.
        """
        muestras = muestras or config.IMU_MUESTRAS_CALIBRACION
        suma = 0.0
        for i in range(muestras):
            suma += self.lector.crudo()
            if mostrar and i % 50 == 0:
                mostrar(i, muestras)
            time.sleep(0.002)
        self.offset = suma / muestras
        self.reiniciar()
        return self.offset

    def reiniciar(self):
        """Zero the accumulated angle."""
        self.grados = 0.0
        self._ultimo = time.time()

    def actualizar(self):
        """Read the sensor and integrate. Call once per control loop."""
        ahora = time.time()
        dt = ahora - self._ultimo
        self._ultimo = ahora

        velocidad = (self.lector.crudo() - self.offset) * self.escala

        # Dead band: below this much noise the robot counts as still, so
        # the angle does not drift while it is driving straight.
        if abs(velocidad) < config.IMU_ZONA_MUERTA:
            velocidad = 0.0

        self.velocidad = velocidad
        self.grados += velocidad * dt
        return self.grados

    def es_esquina(self):
        """True when the accumulated turn passes the corner threshold.

        Keeps the threshold test and the angle reset in one place. They
        used to be copied into both race programs, which is how two
        copies of the same logic end up drifting apart.

        It also discards false corners. The gyroscope cannot tell a track
        corner from a block avoidance manoeuvre: when the camera sends
        the steering to full lock, the robot really does turn and really
        does accumulate 87 degrees. Measured on track: two corners 1.1 s
        apart, where the real ones were coming every 6 s.

        So a corner arriving sooner than ESQUINA_INTERVALO_MINIMO is
        treated as false. The angle is reset anyway, because that turn
        physically happened and carrying it forward would add to the next
        corner and trigger it early.

        Call once per control loop, after actualizar().
        """
        if abs(self.grados) < config.ANGULO_ESQUINA:
            return False

        ahora = time.time()
        if ahora - self._ultima_esquina < config.ESQUINA_INTERVALO_MINIMO:
            self.esquinas_descartadas += 1
            self.reiniciar()
            return False

        self._ultima_esquina = ahora
        self.reiniciar()
        return True

    @property
    def vueltas(self):
        return self.grados / 360.0
