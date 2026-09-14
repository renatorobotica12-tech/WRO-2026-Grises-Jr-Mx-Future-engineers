"""HuskyLens leida a traves del adaptador OFDL.

https://github.com/ofdl-robotics-tw/EV3-HuskyLens-Stuff

El adaptador lleva un Arduino Pro Mini que traduce los datos de la
HuskyLens al protocolo LEGO UART. Para el EV3 es un sensor normal, asi
que ev3dev lo detecta solo: no hay que tocar el modo del puerto ni
instalar drivers, a diferencia del I2C del Nano.

Medido en el robot: ev3dev lo ve como driver `ev3-uart-84`, con los modos
`Data-EV3HSK` y `Time-EV3HSK`, y entrega **ocho** valores s32, no seis.

El orden real **no** es el que dice el README del adaptador. Es:

    0 X   1 Y   2 W   3 H   4 ID   5 State   6 y 7 sin usar

Se lee `bin_data` en vez de ocho `value(i)`: es una sola lectura atomica
de 32 bytes, asi que no se mezclan datos de dos fotogramas, y ademas
tarda 5 ms en vez de 49 ms. A 49 ms la camara sola dejaria el lazo de
control en 20 Hz.

Codigos de State segun el README del adaptador:

    9  adaptador conectado pero HuskyLens no
    8  conectada, sin objetos aprendidos
    7  conectada y con objetos aprendidos, pero no ve ninguno
    1  hay objeto detectado
    0  puerto desconectado o perdida de datos
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
        self.x = 0.0                 # centrado en 0, negativo a la izquierda
        self.y = 0.0
        self.ancho = 0
        self.alto = 0

        # Estado de la retencion. Ver angulo_esquive_retenido().
        self.reteniendo = False      # solo para la telemetria
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
        """Los ocho valores en una sola lectura atomica de bin_data."""
        with open(self.ruta + '/bin_data', 'rb') as f:
            return struct.unpack(self.formato, f.read(self.bytes))

    def actualizar(self):
        """Equivale al procedimiento `actualizar Huskylens` de Arath.

        Devuelve True si hay un objeto detectado.
        """
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

        # La inversion va aqui, sobre la coordenada ya centrada en 0, y no
        # mas adelante: asi todo lo que viene despues (targets, recortes,
        # signo del volante) sigue significando lo mismo con cualquier
        # lente. Cambiar el lente no deberia obligar a retocar el resto.
        if config.HUSKY_INVERTIR_X:
            self.x = -self.x
        if config.HUSKY_INVERTIR_Y:
            self.y = -self.y

        self.ancho = valores[config.HUSKY_IDX_W]
        self.alto = valores[config.HUSKY_IDX_H]
        return True

    @property
    def color(self):
        """Nombre del color visto, para la telemetria."""
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
        """Angulo de volante para esquivar el bloque que esta viendo.

        Es un proporcional sobre la posicion del bloque en la imagen: el
        error es lo que le falta al bloque para llegar a su target, y el
        volante corrige hasta anularlo.

            error  = X - target
            angulo = constrain(map(error, -160,160, -tope,+tope), lo, hi)

        Misma forma que la de Arath, que escribe map(X +- 100, ...): su
        desplazamiento es este target con el signo cambiado.

        El target sale de config por color y es EL mando para ajustar
        cuanto se abre el rodeo. Cual signo va con cual lado se fijo
        probando en pista, no deduciendolo: la primera version razonada
        los pasaba por el lado contrario.

        Aqui el centro del volante es 0 y no 90, asi que los limites del
        constrain van tambien referidos a 0.

        Devuelve None si el ID visto no es ninguno de los dos configurados.
        """
        target = self.target()
        if target is None:
            return None

        recorte = (config.HUSKY_LIMITE_VERDE
                   if self.id == config.HUSKY_ID_VERDE
                   else config.HUSKY_LIMITE_ROJO)

        # Los recortes vienen en fracciones del tope, no en grados.
        minimo = recorte[0] * config.VOLANTE_LIMITE
        maximo = recorte[1] * config.VOLANTE_LIMITE

        angulo = map_range(self.x - target,
                           -config.HUSKY_CENTRO_X, config.HUSKY_CENTRO_X,
                           -config.VOLANTE_LIMITE, config.VOLANTE_LIMITE)
        return constrain(angulo, minimo, maximo)

    def angulo_esquive_retenido(self):
        """angulo_esquive() que aguanta los fallos cortos de la camara.

        Es el mismo patron de tres estados que `_filtrar()` aplica a los
        ultrasonicos en ultrasonics.py, y por la misma razon: un fallo de
        una trama no significa que el bloque se haya ido.

            lectura buena  -> se usa y se guarda
            fallo corto    -> se conserva la ultima orden buena
            fallo largo    -> se suelta el mando al seguimiento de pared

        Ademas engancha el bloque. Con dos a la vista, el adaptador OFDL no
        devuelve siempre el mismo recuadro: va cambiando de uno a otro, y
        sin enganche el robot recibe ordenes de lados opuestos en vueltas
        consecutivas. Medido: id=1 pidiendo +50.6 (derecha) y 300 ms
        despues id=2 pidiendo -27.2 (izquierda).

        El mando solo cambia de bloque cuando el nuevo se ve claramente
        MAS ANCHO, por HUSKY_MARGEN_ANCHO. El ancho es el unico dato de
        proximidad que hay: los pilares son todos iguales, asi que mas
        ancho es mas cerca, y el mas cercano es el que urge esquivar. Es
        el criterio de "el recuadro mas ancho" que usa Arath, recuperado
        comparando entre lecturas en vez de dentro de una sola.

        La ventana de tiempo NO sirve para esto: se probo alargarla de 0.1
        a 0.3 s y el alternado siguió igual, porque ocurre a escalas mas
        largas que cualquier ventana razonable. Solo añadia retraso.

        Devuelve None cuando de verdad no hay nada que esquivar, igual que
        angulo_esquive(), que se deja intacto para el diagnostico crudo de
        `check_hw.py husky`.
        """
        ahora = time.time()
        vigente = (self._ultimo_angulo is not None
                   and ahora - self._marca_angulo <= config.HUSKY_RETENCION)

        if self.hay_objeto:
            # Otro bloque mientras el enganchado sigue vigente: solo se le
            # cede el mando si esta mas cerca que el que se esta esquivando.
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
        """Donde debe quedar el bloque en la imagen, segun su color.

        None si el ID visto no es ninguno de los dos configurados.
        """
        if self.id == config.HUSKY_ID_VERDE:
            return config.HUSKY_TARGET_VERDE
        if self.id == config.HUSKY_ID_ROJO:
            return config.HUSKY_TARGET_ROJO
        return None
