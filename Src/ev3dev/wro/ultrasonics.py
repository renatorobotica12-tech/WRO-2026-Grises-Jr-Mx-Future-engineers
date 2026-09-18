"""Reading the Arduino Nano that multiplexes the five ultrasonic sensors.

There are two paths, depending on which firmware the Nano is running:

  'serial' -> ultrasonic_hub_serial, plugged into the brick's USB port
  'i2c'    -> ultrasonic_hub_packet or ultrasonic_hub, on a sensor port

Serial is the recommended path. The I2C on the EV3 sensor ports is not
hardware: the brick bit-bangs it in software and it runs at a few kHz.
Going over USB at 115200 baud also frees up a sensor port.
"""

import glob
import math
import time

from . import config, i2c, ports

# Which sensor can stand in for which, and by how much.
#
# Each side carries a perpendicular sensor and one at 25 degrees, both
# looking at the same wall, so r25 = r90 / cos(25). Built from the port
# mapping rather than written out, so re-mapping the sensors in config
# carries these with it.
_COS25 = math.cos(math.radians(25))
_PAREJAS = {}
for _perp, _ang in ((config.IDX_IZQ[0], config.IDX_IZQ[1]),
                    (config.IDX_DER[1], config.IDX_DER[0])):
    _PAREJAS[_ang] = (_perp, 1.0 / _COS25)   # estimate the 25 from the 90
    _PAREJAS[_perp] = (_ang, _COS25)         # and the 90 from the 25


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
        self.lecturas_fallidas = 0      # reads that raised, see actualizar()
        self.estimados = [0] * 5        # readings taken from the partner
        self.pesimistas = 0             # front readings held, see _frente_pesimista

    # ----------------------------------------------------------------
    # Reading: the subclass implements _leer()
    # ----------------------------------------------------------------

    def actualizar(self):
        """Read once and filter. Never raises on a bad read.

        A read that fails is treated exactly like a frame that did not
        arrive, because that is what it is. Letting the exception out
        ends the run instead, and it did, on track:

            serial.serialutil.SerialException: read failed: device
            reports readiness to read but returned no data

        in the middle of an approach, with the robot centimetres from a
        wall. The filter already knows how to cope with a missing frame
        -- it holds the last good reading for ARD_RETENCION and then
        falls back to "no wall nearby" -- so a dropped read is a case it
        is built for, and one bad read is not a reason to abandon a run.

        The failures are counted rather than hidden. A handful across a
        run is a glitch; a steady stream is a cable, a connector, or the
        Nano browning out, and the count is what tells those apart.
        """
        try:
            ok = self._leer()
        except Exception:
            self.lecturas_fallidas += 1
            ok = False
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
                # Too long without an echo. Before concluding there is
                # no wall, ask this sensor's partner.
                #
                # The two sensors on a side look at the SAME wall, one
                # perpendicular and one at 25 degrees, so either can
                # estimate the other:
                #
                #     r25 = r90 / cos(25) = 1.103 * r90
                #
                # This matters more than it sounds. Substituting
                # ARD_DISTANCIA_MAXIMA puts 100 cm into one side of an
                # error built from four readings, which swings it by
                # about that much. A track run showed the cost: one
                # sensor lost its echo on 777 frames out of 3483, 22 %
                # of the run, and the centring error swung to -183 and
                # +181 in a one metre corridor where it cannot exceed
                # about 100. The steering spent the race pinned to its
                # stop, following the substitution rather than the wall.
                #
                # The partner is only used when it has a real reading of
                # its own. Two failed sensors on one side still means no
                # wall.
                estimado = self._estimar_de_pareja(i, ahora)
                if estimado is not None:
                    valor = estimado
                    self.estimados[i] += 1
                elif self._frente_pesimista(i, ahora):
                    # The front sensor, still holding its last reading
                    # well past ARD_RETENCION. See _frente_pesimista().
                    valor = self.ultimo_bueno[i]
                    self.pesimistas += 1
                else:
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

    def _frente_pesimista(self, i, ahora):
        """Should the front sensor keep its last reading instead of
        being declared clear?

        The front sensor has no partner, and for it the two possible
        substitutions are not equally safe.

        An ultrasonic aimed obliquely at a wall gets no echo back: the
        pulse reflects away rather than returning. So the front sensor
        falls silent exactly when the robot arrives at a wall at an
        angle -- the moment its reading matters most -- and it also
        falls silent below about 2 cm, when the wall is as close as it
        can be. In both cases silence means "wall", and substituting
        ARD_DISTANCIA_MAXIMA tells the robot the opposite.

        That is what was happening on track. The front lost its echo,
        the filter reported 100 cm, and the collision guard stopped
        reacting to a wall that was still there; the run was saved by
        someone picking the robot up.

        So a silent front keeps its last good reading, which is
        pessimistic and therefore safe, for ARD_FRENTE_PESIMISTA_S. Past
        that the silence probably is an empty corridor -- a wall does
        not stay unmeasurable for seconds while the robot moves -- and
        the normal substitution takes over, because a robot that creeps
        for ever because of one stale reading is no use either.
        """
        if not config.ARD_FRENTE_PESIMISTA:
            return False
        if i != config.IDX_FRONTAL:
            return False
        if self.ultimo_bueno[i] is None:
            return False
        return (ahora - self.marca_bueno[i]
                <= config.ARD_FRENTE_PESIMISTA_S)

    def _estimar_de_pareja(self, i, ahora):
        """Estimate sensor `i` from the other one on its side.

        Returns None when there is no partner, when the partner has no
        recent reading of its own, or when the feature is switched off.

        The pairs come from IDX_IZQ and IDX_DER, and within each the
        perpendicular one and the 25 degree one see the same wall. The
        conversion is the same cosine the wall-centring geometry uses,
        so this introduces no new assumption about the track: if the
        robot is far from parallel both readings are wrong together
        anyway, and the estimate is no worse than the sensor it stands
        in for.
        """
        if not config.ARD_ESTIMAR_PAREJA:
            return None

        pareja = _PAREJAS.get(i)
        if pareja is None:
            return None
        otro, factor = pareja

        # The partner must have a reading of its own from this frame or
        # very recently -- not one that is itself a substitution.
        if self.ultimo_bueno[otro] is None:
            return None
        if ahora - self.marca_bueno[otro] > config.ARD_RETENCION:
            return None

        return min(self.ultimo_bueno[otro] * factor,
                   config.ARD_DISTANCIA_MAXIMA)

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

    @property
    def frontal_crudo(self):
        """The front sensor's own latest number, unfiltered. None if the
        last frame had no echo.

        `frontal` is the right reading for steering: the median kills
        spikes and the hold rides out dropouts, and neither matters over
        the distances wall following works at.

        It is the wrong reading for stopping close to something. Both of
        those mechanisms delay the fall. Closing on a wall, the echo
        starts failing before the robot arrives, and the filter answers
        with the last GOOD value -- four centimetres, say -- for
        ARD_RETENCION afterwards. A threshold below that is never
        crossed, and the robot keeps going while the reading insists it
        has not arrived yet.

        This returns what the sensor measured on the last frame, or None
        when it measured nothing. A caller that has to react at a
        distance rather than track one wants this.
        """
        i = config.IDX_FRONTAL
        if not self.valido(i):
            return None
        crudo = self.distancias[i]
        if crudo >= config.ARD_FUERA_DE_RANGO:
            return None
        return crudo

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
