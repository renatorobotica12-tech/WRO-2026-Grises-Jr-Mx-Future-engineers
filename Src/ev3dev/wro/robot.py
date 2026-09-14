"""Drive train and steering.

Steering is an EV3 medium motor driven as if it were a servo: it is
given an absolute position command in degrees relative to centre, and
the EV3's own position controller does the rest.
"""

from ev3dev2.motor import Motor
from ev3dev2.led import Leds

from . import config
from .util import clamp_abs, constrain


class Robot(object):
    """`Motor` is used rather than `LargeMotor` / `MediumMotor` on purpose.

    Those two classes filter by `driver_name`, so `LargeMotor` throws on
    a medium motor. Both motors on this robot are medium ones, and in any
    case nothing in this file depends on motor size: the drive train is
    commanded 0 to 100 and the steering by position.
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
    # Steering
    # ----------------------------------------------------------------

    def preparar_volante(self):
        """Establish the steering centre before a run.

        With VOLANTE_AUTOCENTRAR False, the steering is assumed to have
        been straight at power-on and that point becomes zero. With True,
        both mechanical stops are found and zero is the midpoint, which
        is reliable even if the robot was stored with the wheels turned.
        """
        if config.VOLANTE_AUTOCENTRAR:
            self.centro = self._buscar_centro()

            # A warning, not an error. A short travel can mean the search
            # never reached the stops and the centre is meaningless, but
            # it can also be a false alarm. The comparison uses the
            # FORCED travel, the only one that always goes stop to stop:
            # the free travel comes out short when the steering starts
            # already against a stop, because the first push on that side
            # then covers very little.
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
        """Push the steering against one stop; return (position, moved).

        The whole ladder of duty cycles is ALWAYS walked, lowest to
        highest, keeping the final position. That is the part that
        matters: the steering ceasing to move at a low duty cycle does
        NOT mean it reached the stop, only that this much power no longer
        pushes it further. Measured on this robot:

            25 %  does not move at all
            40 %  advances 28 degrees and jams halfway
            60 %  reaches 119
            100 % reaches 125          <- this is the real stop

        An earlier version stopped as soon as it saw movement and
        accepted the 28 as the stop, which measured 26 degrees of travel
        instead of 111 and put the centre almost 50 degrees off.

        The "not moving" timer only starts AFTER the steering has been
        seen to move. Starting it earlier confuses the static friction of
        the first few milliseconds with a mechanical stop.
        """
        import time

        UMBRAL = 1
        QUIETO = 0.3          # short, so it is not left straining
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
        """Find both mechanical stops; set self.topes and self.recorrido.

        Both positions are measured from the SAME origin: `reset()` runs
        once, before starting. Resetting the encoder between one stop and
        the other would make the midpoint meaningless.

        Two travels are recorded, and the difference between them
        matters:

          self.recorrido        stop to stop, pushing at full power
          self.recorrido_libre  how far it gets at the lowest power

        Measured on this robot: 157 forced against 111 free. Those 46
        degrees of difference are the mechanism flexing against the
        stops, not usable steering. VOLANTE_LIMITE has to come from the
        free travel; taking it from the forced one produces a limit that
        makes the steering fight the stops on every correction.

        The centre comes from the forced travel, which is the more
        symmetric of the two: both ends are reached the same way, whereas
        the free ends are reached one from the centre and one from a stop.

        Returns the midpoint. Used both by the start-up auto-centring and
        by `check_hw.py topes`, so there is a single implementation and
        the two cannot drift apart again.
        """
        self.volante.reset()
        self.volante.stop_action = 'coast'

        extremo_a, libre_a, movio_a = self.empujar_a_tope(+1, avisar)
        extremo_b, libre_b, movio_b = self.empujar_a_tope(-1, avisar)

        # Do not assume positive power raises the position: on this robot
        # it lowers it. The ends are ordered by value instead.
        self.topes = (min(extremo_a, extremo_b), max(extremo_a, extremo_b))
        self.recorrido = self.topes[1] - self.topes[0]
        self.recorrido_libre = abs(libre_a - libre_b)
        self.movio = (movio_a, movio_b)

        self.volante.stop_action = 'hold'
        # The steering was driven with run_direct, so any stored position
        # command is no longer valid.
        self._destino_volante = None
        return int(round((extremo_a + extremo_b) / 2.0))

    def _buscar_centro(self):
        return self.medir_topes()

    def resumen_topes(self):
        """What the auto-centring measured, ready to print.

        Called after preparar_volante(). It lives here rather than being
        copied into each program so all three report the same thing, and
        so `check_hw.py topes` and the start of a race cannot disagree
        about what these numbers mean.

        Worth reading on every run: if the mechanism works loose or the
        motor slips, these values change before the symptom shows up on
        track.
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
        """Steering command, in degrees relative to centre.

        Positive turns right, negative left. The value is clamped to the
        per-side limits before anything else happens.

        The command is only written when it CHANGES, same as in
        avanzar(). `run_to_abs_pos()` is a persistent order: the motor
        keeps driving to that position without the command being
        repeated. Re-issuing it on every control loop restarted the EV3's
        position controller every 22 ms, so the ramp never completed and
        the steering responded in jerks instead of moving cleanly to the
        commanded angle.
        """
        # Clamping is per side. VOLANTE_LIMITE is the mechanical ceiling
        # and the fractions are the tuning knob; with both at 1.0 this is
        # the plain symmetric clamp.
        #
        # It happens HERE because this is the single point both the wall
        # following and the camera avoidance pass through, so no path can
        # bypass the limit.
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
        """Turn the ultrasonic centring error into a steering angle.

        A plain proportional term: angle = kp * error, clamped by girar().
        The gain is explicit and the centre is zero.

        `kp` lets each program use its own: the open challenge and the
        obstacle challenge want different aggressiveness for the same
        error, because in the obstacle run the wall following is only
        what happens between blocks, and a high gain there leaves the
        robot swinging wall to wall just as the camera is about to take
        over.
        """
        if kp is None:
            kp = config.VOLANTE_KP
        self.girar(kp * error_crudo)

    # ----------------------------------------------------------------
    # Drive train
    # ----------------------------------------------------------------

    def avanzar(self, velocidad):
        """Drive forward. `velocidad` is 0 to 100 in both modes.

        With TRACCION_MODO = 'velocidad' the number is a percentage of
        the motor's maximum speed and the EV3 regulates using the
        encoder: if a wheel is slowed by a bump in the track surface, the
        controller raises power until the commanded speed is recovered.

        With 'potencia' the number is the raw duty cycle. That is open
        loop: against an obstacle the power stays the same and the robot
        just stalls. Velocity mode was chosen after the robot kept
        bogging down on track imperfections.

        The command is only written when it changes. At ~44 Hz,
        rewriting identical values into sysfs every loop is wasted work.
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
    # Lap indicator on the brick LEDs
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
