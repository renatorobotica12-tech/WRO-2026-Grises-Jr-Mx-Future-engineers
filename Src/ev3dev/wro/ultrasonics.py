"""Lectura del Arduino Nano multiplexor de cinco ultrasonicos.

Reemplaza al bloque `ARD` de EV3-G y, del lado de Arduino, a las cinco
llamadas a readUltrasound() del procedimiento `Distancia` de Arath.

Hay dos caminos segun el firmware que tenga cargado el Nano:

  'serial' -> ultrasonic_hub_serial, conectado al puerto USB del ladrillo
  'i2c'    -> ultrasonic_hub_packet o ultrasonic_hub, en un puerto de sensores

El camino serial es el recomendado: el I2C de los puertos de sensores del
EV3 se genera por software y va a pocos kHz.
"""

import glob
import time

from . import config, i2c, ports


class _HubBase(object):

    def __init__(self):
        self.distancias = [config.ARD_FUERA_DE_RANGO] * 5   # crudas
        self.utiles = [config.ARD_DISTANCIA_MAXIMA] * 5     # filtradas
        self.validez = 0
        self.trama = -1
        self.tramas_malas = 0
        self.tramas_leidas = 0

        self.ultimo_bueno = [None] * 5
        self.marca_bueno = [0.0] * 5
        self.historia = [[] for _ in range(5)]
        self.sin_eco = [0] * 5          # cuantas veces se sustituyo cada uno

    # ----------------------------------------------------------------
    # Lectura: el subtipo implementa _leer()
    # ----------------------------------------------------------------

    def actualizar(self):
        ok = self._leer()
        if ok:
            self._filtrar()
        return ok

    def _leer(self):
        raise NotImplementedError

    def _filtrar(self):
        """Convierte las lecturas crudas en distancias utilizables.

        Un 125 con el bit de validez bajo no es una distancia: es "no
        hubo eco". Sustituirlo por la ultima lectura buena evita que un
        parpadeo de un sensor mande el volante al tope.
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
                # Parpadeo corto: se conserva lo ultimo bueno.
                valor = self.ultimo_bueno[i]
                self.sin_eco[i] += 1
            else:
                # Lleva demasiado sin eco: de verdad no hay pared cerca.
                valor = config.ARD_DISTANCIA_MAXIMA
                self.sin_eco[i] += 1

            valor = min(valor, config.ARD_DISTANCIA_MAXIMA)

            historia = self.historia[i]
            historia.append(valor)
            if len(historia) > config.ARD_MEDIANA:
                historia.pop(0)
            self.utiles[i] = sorted(historia)[len(historia) // 2]

    # ----------------------------------------------------------------
    # Interpretacion, comun a los dos caminos
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
        """Error de centrado entre paredes, en centimetros.

        Mismo calculo del bloque `ERROR` de EV3-G y del procedimiento
        `Distancia` de Arath, antes del map a grados de servo:

            ((90izq + 25izq) - (25der + 90der)) * -1
        """
        return -(sum(self.izquierda) - sum(self.derecha))

    def cerrar(self):
        pass


class HubSerial(_HubBase):
    """El Nano por USB. Formato: 'U d1 d2 d3 d4 d5 mascara trama xor'."""

    def __init__(self, puerto=None, baudios=None):
        _HubBase.__init__(self)

        import serial

        from .power import AlimentacionNano

        # Primero la corriente y despues el puerto serie. Al reves, el
        # Nano arrancaria con el serie ya abierto y se perderian tramas
        # hasta que terminara de reiniciarse.
        self.alimentacion = AlimentacionNano()
        self.alimentacion.encender()

        self.puerto = puerto or config.ARD_PUERTO_SERIE or self.buscar_puerto()
        self.serie = serial.Serial(self.puerto,
                                   baudios or config.ARD_BAUDIOS,
                                   timeout=0)
        self.buffer = b''
        self.sin_datos = 0

        # El Nano se reinicia al abrir el puerto por la linea DTR.
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
        """Se queda con la ultima linea completa que haya llegado.

        El Nano manda unas 110 lineas por segundo, mas de lo que consume
        el lazo de control. Se descartan las viejas y se usa la mas
        reciente para no acumular retraso.
        """
        pendiente = self.serie.in_waiting
        if pendiente:
            self.buffer += self.serie.read(pendiente)

        if b'\n' not in self.buffer:
            self.sin_datos += 1
            return False

        partes = self.buffer.split(b'\n')
        self.buffer = partes[-1]            # resto incompleto

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
    """El Nano en un puerto de sensores, como esclavo I2C."""

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
            # Mejor un dato de hace 20 ms que un salto a 125 cm que manda
            # el volante al tope.
            self.tramas_malas += 1
            return False

        self.distancias = datos[:5]
        self.validez = datos[5]
        self.trama = datos[6]
        return True

    def _actualizar_byte_a_byte(self):
        """Firmware antiguo: se escribe el numero de sensor y se lee un byte."""
        self.tramas_leidas += 1
        for indice in range(5):
            i2c.escribir_bloque(self.bus, self.direccion_i2c, [indice + 1])
            self.distancias[indice] = i2c.leer_bloque(
                self.bus, self.direccion_i2c, 1)[0]
        self.validez = 0x1F
        return True


def crear_hub():
    """Devuelve el hub segun config.ARD_BACKEND."""
    if config.ARD_BACKEND == 'serial':
        return HubSerial()
    return HubI2C()
