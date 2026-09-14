"""Traccion y volante.

El robot de Arath dirige con un servo de hobby en el pin 8, con angulos
de 70 a 110 y centro en 90. El robot de Renato dirige con un motor
mediano del EV3. Aqui el motor mediano se maneja como si fuera un servo:
se le da una consigna de posicion absoluta en grados respecto del centro
y el control de posicion del propio EV3 se encarga del resto.
"""

from ev3dev2.motor import Motor
from ev3dev2.led import Leds

from . import config
from .util import clamp_abs, constrain


class Robot(object):
    """Se usa `Motor` y no `LargeMotor` / `MediumMotor` a proposito.

    Esas dos clases filtran por `driver_name`, asi que `LargeMotor` revienta
    con un motor mediano. En este robot los dos motores son medianos, y de
    todos modos nada de lo que hace este archivo depende del tamano: la
    traccion va por `duty_cycle_sp` de 0 a 100 y el volante por posicion.
    """

    def __init__(self):
        self.traccion = Motor(config.PUERTO_TRACCION)
        self.volante = Motor(config.PUERTO_VOLANTE)
        self.leds = Leds()

        self.volante.stop_action = 'hold'
        self.traccion.stop_action = 'brake'

        self.centro = 0
        self.topes = (0, 0)
        self.recorrido = 0
        self.recorrido_libre = 0
        self.movio = (False, False)
        self.velocidad = 0.0
        self.angulo_volante = 0.0
        self._destino_volante = None

    # ----------------------------------------------------------------
    # Volante
    # ----------------------------------------------------------------

    def preparar_volante(self):
        """Equivale al bloque `reinicio_volante` de EV3-G.

        Con VOLANTE_AUTOCENTRAR en False se da por hecho que el volante
        quedo recto al encender, y ese punto pasa a ser el cero. Con True
        se buscan los dos topes y el cero es el punto medio, que es fiable
        aunque el robot se haya guardado con las ruedas torcidas.
        """
        if config.VOLANTE_AUTOCENTRAR:
            self.centro = self._buscar_centro()

            # Aviso, no error: un recorrido corto puede significar que la
            # busqueda no encontro los topes y el centro no vale nada,
            # pero tambien puede ser un falso positivo. Se compara contra
            # el recorrido FORZADO, que es el unico que va siempre de
            # tope a tope; el libre se queda corto cuando el volante
            # arranca ya pegado a un tope, porque entonces el primer
            # empujon de ese lado recorre poco.
            if self.recorrido < 2 * config.VOLANTE_LIMITE:
                print('AVISO: el volante solo recorrio %d grados y '
                      'VOLANTE_LIMITE es %.1f. Si el robot va torcido, '
                      'corra `check_hw.py topes`.'
                      % (self.recorrido, config.VOLANTE_LIMITE))
        else:
            self.volante.reset()
            self.centro = 0

        self.volante.stop_action = 'hold'
        self.girar(0)

    def empujar_a_tope(self, signo, avisar=None):
        """Empuja el volante contra un tope y devuelve (posicion, se_movio).

        Se recorre SIEMPRE toda la escalera de potencias, de menor a
        mayor, quedandose con la posicion final. Es la parte que importa:
        que el volante deje de moverse a una potencia baja NO significa
        que haya llegado al tope, solo que esa potencia ya no lo empuja
        mas. Medido en este robot:

            25 %  no se mueve nada
            40 %  avanza 28 grados y se clava a mitad de camino
            60 %  llega a 119
            100 % llega a 125          <- este es el tope de verdad

        Una version anterior cortaba en cuanto veia movimiento y aceptaba
        el 28 como tope, con lo que medía 26 grados de recorrido en vez
        de 111 y el centro salia desplazado casi 50 grados.

        El cronometro de "esta quieto" solo corre DESPUES de haber visto
        moverse el volante: si empieza antes, la friccion estatica de los
        primeros milisegundos se confunde con un tope.
        """
        import time

        UMBRAL = 1
        QUIETO = 0.3          # corto, para no dejarlo clavado mas de la cuenta
        ARRANQUE = 0.6
        LIMITE = 4.0

        partida = self.volante.position

        for duty in config.VOLANTE_DUTIES_CENTRADO:
            antes = self.volante.position
            self.volante.run_direct(duty_cycle_sp=signo * duty)

            ultima = antes
            arranco = False
            sin_moverse = None
            limite = time.time() + LIMITE
            espera = time.time() + ARRANQUE

            while time.time() < limite:
                time.sleep(0.05)
                actual = self.volante.position
                if abs(actual - ultima) >= UMBRAL:
                    ultima = actual
                    arranco = True
                    sin_moverse = time.time()
                elif arranco and time.time() - sin_moverse >= QUIETO:
                    break
                elif not arranco and time.time() > espera:
                    break

            self.volante.stop()

            if avisar:
                avisar('%3d %% -> %+d grados (avanzo %+d)'
                       % (duty, self.volante.position,
                          self.volante.position - antes))

            if duty == config.VOLANTE_DUTIES_CENTRADO[0]:
                libre = self.volante.position

        final = self.volante.position
        return final, libre, abs(final - partida) >= UMBRAL

    def medir_topes(self, avisar=None):
        """Busca los dos topes mecanicos y deja self.topes y self.recorrido.

        Las dos posiciones se miden desde el MISMO origen: el `reset()`
        va una sola vez, antes de empezar. Reiniciando el encoder entre
        un tope y otro, el punto medio no significaria nada.

        Deja dos recorridos, y la diferencia entre ellos importa:

          self.recorrido        tope a tope empujando al maximo
          self.recorrido_libre  hasta donde llega con la potencia minima

        Medido en este robot: 157 forzado contra 111 libre. Los 46 de
        diferencia son el mecanismo flexando contra los topes, no
        direccion utilizable. VOLANTE_LIMITE tiene que salir del libre;
        del forzado saldria un limite que hace pelear al volante con los
        topes en cada correccion.

        El centro se toma del recorrido forzado, que es el mas simetrico:
        los dos extremos se alcanzan del mismo modo, mientras que los
        libres se alcanzan uno desde el centro y otro desde un tope.

        Devuelve el punto medio. Lo usan tanto el autocentrado del
        arranque como `check_hw.py topes`: una sola implementacion, para
        que no puedan volver a discrepar.
        """
        self.volante.reset()
        self.volante.stop_action = 'coast'

        extremo_a, libre_a, movio_a = self.empujar_a_tope(+1, avisar)
        extremo_b, libre_b, movio_b = self.empujar_a_tope(-1, avisar)

        # No se asume que potencia positiva suba la posicion: en este
        # robot la hace bajar. Los extremos se ordenan por su valor.
        self.topes = (min(extremo_a, extremo_b), max(extremo_a, extremo_b))
        self.recorrido = self.topes[1] - self.topes[0]
        self.recorrido_libre = abs(libre_a - libre_b)
        self.movio = (movio_a, movio_b)

        self.volante.stop_action = 'hold'
        # El volante se movio con run_direct, asi que la consigna de
        # posicion que hubiera quedado guardada ya no vale.
        self._destino_volante = None
        return int(round((extremo_a + extremo_b) / 2.0))

    def _buscar_centro(self):
        return self.medir_topes()

    def resumen_topes(self):
        """Lo que midio el autocentrado, listo para imprimir.

        Se llama despues de preparar_volante(). Esta aqui y no copiado en
        cada programa para que los tres reporten lo mismo, y para que
        `check_hw.py topes` y el arranque de una carrera no puedan
        discrepar en lo que significan estos numeros.

        Conviene mirarlo en cada corrida: si el mecanismo se afloja o el
        motor patina, estos valores cambian antes de que el sintoma se
        note en pista.
        """
        if not config.VOLANTE_AUTOCENTRAR:
            return 'volante: sin autocentrar, el cero es donde arranco'

        bajo, alto = self.topes
        sugerido = (self.recorrido_libre / 2.0) * 0.85
        return '\n'.join([
            'tope bajo         : %+d grados' % bajo,
            'tope alto         : %+d grados' % alto,
            'centro            : %+d grados respecto de donde arranco'
            % self.centro,
            'recorrido forzado : %d grados, empujando al 100 %%'
            % self.recorrido,
            'recorrido libre   : %d grados, a potencia minima'
            % self.recorrido_libre,
            'VOLANTE_LIMITE    : %.1f en uso; esta medicion sugiere %.1f'
            % (config.VOLANTE_LIMITE, sugerido),
            'recorte por lado  : derecha %+.1f, izquierda %+.1f'
            % (config.VOLANTE_LIMITE * config.VOLANTE_FRACCION_DERECHA,
               -config.VOLANTE_LIMITE * config.VOLANTE_FRACCION_IZQUIERDA),
        ])

    def girar(self, grados):
        """Consigna del volante en grados respecto del centro.

        `grados` positivo o negativo dentro de +-VOLANTE_LIMITE.
        Reemplaza a Volante(%n) de Arduino y a PID_R_20 de EV3-G.

        La consigna solo se escribe cuando CAMBIA, igual que en avanzar().
        `run_to_abs_pos()` es una orden que persiste: el motor sigue yendo
        a esa posicion sin que haya que repetirla. Reemitirla en cada
        vuelta de lazo reiniciaba el controlador de posicion del EV3 cada
        22 ms, con lo que la rampa no llegaba a completarse nunca y el
        volante respondia a tirones en vez de ir limpio a la consigna.
        """
        # El recorte va por lado. VOLANTE_LIMITE es el techo mecanico y
        # las fracciones el mando de ajuste; con las dos en 1.0 esto
        # equivale al recorte simetrico de siempre.
        #
        # Se recorta AQUI, que es por donde pasan tanto el seguimiento de
        # pared como el esquive con camara: asi no hay forma de que algun
        # camino se salte el limite.
        tope_derecha = config.VOLANTE_LIMITE * config.VOLANTE_FRACCION_DERECHA
        tope_izquierda = (config.VOLANTE_LIMITE
                          * config.VOLANTE_FRACCION_IZQUIERDA)
        grados = constrain(grados, -tope_izquierda, tope_derecha)
        self.angulo_volante = grados
        destino = int(round(self.centro
                            + config.VOLANTE_SIGNO * grados
                            + config.VOLANTE_TRIM))

        if destino == self._destino_volante:
            return
        self._destino_volante = destino

        self.volante.speed_sp = config.VOLANTE_VELOCIDAD
        self.volante.position_sp = destino
        self.volante.run_to_abs_pos()

    def girar_por_error(self, error_crudo, kp=None):
        """Convierte el error de los ultrasonicos en angulo de volante.

        Arath hace map(error, -100, 100, 90-20, 90+20), que es una
        ganancia de 0.2 grados por unidad de error alrededor del centro.
        Aqui la ganancia es explicita y el centro es el cero.

        `kp` deja que cada programa use la suya: la prueba abierta y la de
        obstaculos quieren agresividades distintas para el mismo error.
        """
        if kp is None:
            kp = config.VOLANTE_KP
        self.girar(kp * error_crudo)

    # ----------------------------------------------------------------
    # Traccion
    # ----------------------------------------------------------------

    def avanzar(self, velocidad):
        """Avanza. `velocidad` va de 0 a 100 en los dos modos.

        Con TRACCION_MODO = 'velocidad' el numero es el porcentaje de la
        velocidad maxima del motor y el EV3 regula por encoder: si la
        rueda se frena contra una imperfeccion de la pista, el
        controlador sube la potencia hasta recuperar la velocidad pedida.

        Con 'potencia' es el ciclo de trabajo directo, que es lo que hace
        Arath con su PWM. Es lazo abierto: ante un obstaculo la potencia
        sigue siendo la misma y el robot se queda clavado. Su motor no
        tiene encoder y no puede hacer otra cosa; este si.

        La consigna solo se escribe cuando cambia. A 44 Hz, reescribir
        los mismos valores en sysfs cada vuelta es trabajo tirado.
        """
        velocidad = clamp_abs(velocidad, 100)
        if velocidad == self.velocidad:
            return
        self.velocidad = velocidad

        if config.TRACCION_MODO == 'velocidad':
            self.traccion.speed_sp = int(round(
                velocidad / 100.0 * self.traccion.max_speed))
            self.traccion.run_forever()
        else:
            self.traccion.run_direct(duty_cycle_sp=int(round(velocidad)))

    def frenar(self):
        self.velocidad = 0.0
        self.traccion.stop(stop_action='brake')

    def apagar(self):
        self.frenar()
        self.girar(0)
        self.volante.stop(stop_action='coast')
        self._destino_volante = None

    # ----------------------------------------------------------------
    # Indicadores: sustituyen a la tira WS2812 de Arath
    # ----------------------------------------------------------------

    def indicar_vuelta(self, esquinas):
        if esquinas >= 12:
            color = 'RED'
        elif esquinas >= 8:
            color = 'AMBER'
        elif esquinas >= 4:
            color = 'YELLOW'
        else:
            color = 'GREEN'
        self.leds.set_color('LEFT', color)
        self.leds.set_color('RIGHT', color)
