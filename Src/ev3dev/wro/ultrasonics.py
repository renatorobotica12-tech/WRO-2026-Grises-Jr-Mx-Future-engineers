"""Reading the Arduino Nano that multiplexes the five ultrasonic sensors.

There are two paths, depending on which firmware the Nano is running:

  'serial' -> ultrasonic_hub_serial, plugged into the brick's USB port
  'i2c'    -> ultrasonic_hub_packet or ultrasonic_hub, on a sensor port

Serial is the recommended path. The I2C on the EV3 sensor ports is not
hardware: the brick bit-bangs it in software and it runs at a few kHz.
Going over USB at 115200 baud also frees up a sensor port.
"""

import glob
import time

from . import config, i2c, ports


class _HubBase(object):

    def __init__(self):
        self.distancias = [config.ARD_FUERA_DE_RANGO] * 5   # raw
        self.utiles = [config.ARD_DISTANCIA_MAXIMA] * 5     # filtered
        self.validez = 0
        self.trama = -1
        self.tramas_malas = 0
        self.tramas_leidas = 0

        self.ultimo_bueno = [None] * 5
        self.marca_bueno = [0.0] * 5
        self.historia = [[] for _ in range(5)]
        self.sin_eco = [0] * 5          # substitutions made, per sensor

    # ----------------------------------------------------------------
    # Reading: the subclass implements _leer()
    # ----------------------------------------------------------------

    def actualizar(self):
        ok = self._leer()
        if ok:
            self._filtrar()
        return ok

    def _leer(self):
        raise NotImplementedError

    def _filtrar(self):
        """Turn raw readings into usable distances.

        A 125 with its validity bit low is not a distance: it means "no
        echo came back". Feeding that number straight into the steering
        error makes one sensor dropout look like an 80 cm jump, and the
        steering slams to full lock. Substituting the last good reading
        instead keeps a brief dropout from doing that.
        """
        if not config.ARD_FILTRAR:
            self.utiles = list(self.distancias)
            return

        ahora = time.time()
        for i in range(5):
            crudo = self.distancias[i]

            if self.valido(i) and crudo < config.ARD_FUERA_DE_RANGO:
                self.ultimo_bueno[i] = crudo
                self.marca_bueno[i] = ahora
                valor = crudo
            elif (self.ultimo_bueno[i] is not None
                  and ahora - self.marca_bueno[i] <= config.ARD_RETENCION):
                # Short dropout: hold the last good reading.
                valor = self.ultimo_bueno[i]
                self.sin_eco[i] += 1
            else:
                # Too long without an echo: there really is no wall near.
                valor = config.ARD_DISTANCIA_MAXIMA
                self.sin_eco[i] += 1

            valor = min(valor, config.ARD_DISTANCIA_MAXIMA)

            historia = self.historia[i]
            historia.append(valor)
            if len(historia) > config.ARD_MEDIANA:
                historia.pop(0)
            self.utiles[i] = sorted(historia)[len(historia) // 2]

    # ----------------------------------------------------------------
    # Interpretation, shared by both paths
    # ----------------------------------------------------------------

    def valido(self, indice):
        return bool(self.validez & (1 << indice))

    @property
    def izquierda(self):
        return [self.utiles[i] for i in config.IDX_IZQ]

    @property
    def derecha(self):
        return [self.utiles[i] for i in config.IDX_DER]

    @property
    def frontal(self):
        return self.utiles[config.IDX_FRONTAL]

    def error_crudo(self):
        """Centring error between the corridor walls, in centimetres.

            ((left 90 + left 25) - (right 25 + right 90)) * -1

        The sign is what makes the rest of the chain work: if the robot
        drifts towards the left wall, the left readings drop, the error
        comes out POSITIVE, and a positive steering command turns right,
        away from the wall.

        Each side sums two sensors, so a sideways drift moves all four at
        once: two get closer while two get further away. That is why the
        error grows about four times faster than the actual displacement.
        """
        return -(sum(self.izquierda) - sum(self.derecha))

    def cerrar(self):
        pass


class HubSerial(_HubBase):
    """The Nano over USB. Line format: 'U d1 d2 d3 d4 d5 mask frame xor'."""

    def __init__(self, puerto=None, baudios=None):
        _HubBase.__init__(self)

        import serial

        from .power import AlimentacionNano

        # Power first, serial port second. The other way round, the Nano
        # would boot with the serial link already open and frames would
        # be lost until it finished restarting.
        self.alimentacion = AlimentacionNano()
        self.alimentacion.encender()

        self.puerto = puerto or config.ARD_PUERTO_SERIE or self.buscar_puerto()
        self.serie = serial.Serial(self.puerto,
                                   baudios or config.ARD_BAUDIOS,
                                   timeout=0)
        self.buffer = b''
        self.sin_datos = 0

        # Opening the port toggles DTR, which resets the Nano.
        import time
        time.sleep(config.ARD_ESPERA_ARRANQUE)
        self.serie.reset_input_buffer()

    @staticmethod
    def buscar_puerto():
        for patron in ('/dev/ttyUSB*', '/dev/ttyACM*'):
            encontrados = sorted(glob.glob(patron))
            if encontrados:
                return encontrados[0]
        raise IOError('no se encontro el Nano; revise el cable USB y '
                      'dmesg | tail despues de conectarlo')

    def _leer(self):
        """Keep the most recent complete line that arrived.

        The Nano sends about 110 lines per second, far more than the
        control loop consumes. Older lines are discarded and only the
        newest is used, so latency does not build up in the buffer.
        """
        pendiente = self.serie.in_waiting
        if pendiente:
            self.buffer += self.serie.read(pendiente)

        if b'\n' not in self.buffer:
            self.sin_datos += 1
            return False

        partes = self.buffer.split(b'\n')
        self.buffer = partes[-1]            # incomplete remainder

        for linea in reversed(partes[:-1]):
            if self._parsear(linea):
                self.sin_datos = 0
                return True

        return False

    def _parsear(self, linea):
        self.tramas_leidas += 1
        campos = linea.strip().split()

        if len(campos) != 9 or campos[0] != b'U':
            self.tramas_malas += 1
            return False

        try:
            numeros = [int(c) for c in campos[1:]]
        except ValueError:
            self.tramas_malas += 1
            return False

        checksum = 0
        for numero in numeros[:7]:
            checksum ^= numero

        if checksum != numeros[7]:
            self.tramas_malas += 1
            return False

        self.distancias = numeros[:5]
        self.validez = numeros[5]
        self.trama = numeros[6]
        return True

    def cerrar(self):
        self.serie.close()
        self.alimentacion.apagar()


class HubI2C(_HubBase):
    """The Nano on a sensor port, acting as an I2C slave."""

    def __init__(self, direccion_puerto=None, direccion_i2c=None,
                 firmware=None):
        _HubBase.__init__(self)

        self.direccion_puerto = direccion_puerto or config.PUERTO_ARD
        self.direccion_i2c = direccion_i2c or config.ARD_DIRECCION
        self.firmware = firmware or config.ARD_FIRMWARE

        ports.poner_other_i2c(self.direccion_puerto)
        self.bus = i2c.abrir(self.direccion_puerto)

    def _leer(self):
        if self.firmware == 'packet':
            return self._actualizar_trama()
        return self._actualizar_byte_a_byte()

    def _actualizar_trama(self):
        datos = i2c.leer_bloque(self.bus, self.direccion_i2c, 8)
        self.tramas_leidas += 1

        checksum = 0
        for byte in datos[:7]:
            checksum ^= byte

        if checksum != datos[7]:
            # A reading 20 ms old beats a corrupt jump to 125 cm, which
            # would send the steering to full lock.
            self.tramas_malas += 1
            return False

        self.distancias = datos[:5]
        self.validez = datos[5]
        self.trama = datos[6]
        return True

    def _actualizar_byte_a_byte(self):
        """Older firmware: write the sensor number, then read one byte."""
        self.tramas_leidas += 1
        for indice in range(5):
            i2c.escribir_bloque(self.bus, self.direccion_i2c, [indice + 1])
            self.distancias[indice] = i2c.leer_bloque(
                self.bus, self.direccion_i2c, 1)[0]
        self.validez = 0x1F
        return True


def crear_hub():
    """Return the hub selected by config.ARD_BACKEND."""
    if config.ARD_BACKEND == 'serial':
        return HubSerial()
    return HubI2C()
