"""Drive train and steering.

Steering is an EV3 medium motor driven as if it were a servo: it is
given an absolute position command in degrees relative to centre, and
the EV3's own position controller does the rest.
"""

import math
import time

from ev3dev2.motor import Motor
from ev3dev2.led import Leds

from . import config
from .util import clamp_abs, constrain


class Robot(object):
    """`Motor` is used rather than `LargeMotor` / `MediumMotor` on purpose.

    Those two classes filter by `driver_name`, so `LargeMotor` throws on
    a medium motor. Both motors on this robot are medium ones, and in any
    case nothing in this file depends on motor size: the drive train is
    commanded by ground speed and the steering by position.
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
        self._aviso_saturacion = False
        self.recorrido_retroceso = 0
        self.anticipando = False

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
            'topes declarados  : izquierda %+.1f, centro 0, derecha %+.1f'
            % (config.VOLANTE_TOPE_IZQUIERDO, config.VOLANTE_TOPE_DERECHO),
            'medicion de ahora : sugiere %+.1f por lado' % sugerido,
        ])

    def girar(self, grados, limite=None):
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
        # The two stops, declared in config, in degrees:
        #
        #       -50  <--  0  -->  +50
        #
        # Clamping happens HERE because this is the single point the wall
        # following, the corner anticipation and the camera avoidance all
        # pass through, so no path can bypass it.
        izquierdo = config.VOLANTE_TOPE_IZQUIERDO
        derecho = config.VOLANTE_TOPE_DERECHO

        # `limite` widens the clamp for a caller that has a reason to
        # need more lock than the race does. The parking manoeuvre is
        # the case it was added for: it asks for everything the
        # mechanism has, for a few seconds, at walking pace between two
        # walls. How far the steering should swing at 40 % down a
        # corridor is a different question with a different answer, and
        # the two were sharing one number.
        #
        # It WIDENS the clamp; it does not remove it. Every path still
        # arrives here and still leaves bounded, which is what the note
        # above is protecting. A caller that passes nothing gets exactly
        # the behaviour this method always had.
        if limite is not None:
            derecho = abs(limite)
            izquierdo = -abs(limite)

        grados = constrain(grados, izquierdo, derecho)
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

    def velocidad_maxima(self):
        """Top ground speed of this robot, in the configured unit.

        In cm/s this is a real ceiling: ask for more and the motor
        cannot deliver it, so the robot would run slower than the number
        says and the whole point of using centimetres would be lost.
        """
        if config.VELOCIDAD_UNIDAD != 'cm_s':
            return 100.0
        circunferencia_cm = math.pi * config.RUEDA_TRASERA_DIAMETRO / 10.0
        return (self.traccion.max_speed / 360.0
                / config.TRACCION_REDUCCION * circunferencia_cm)

    def grados_por_segundo(self, velocidad):
        """Convert a speed in the configured unit into motor degrees/s.

        In cm/s, with $C$ the rear wheel circumference and $n$ the
        reduction between motor and wheel:

            wheel turns per second = v / C
            motor turns per second = v / C * n
            motor degrees per second = v / C * n * 360

        In 'porcentaje' it is the old proportion of the motor maximum.
        """
        if config.VELOCIDAD_UNIDAD == 'cm_s':
            circunferencia_cm = math.pi * config.RUEDA_TRASERA_DIAMETRO / 10.0
            return (velocidad / circunferencia_cm
                    * config.TRACCION_REDUCCION * 360.0)
        return velocidad / 100.0 * self.traccion.max_speed

    def girar_por_pared(self, error, frontal, espacio_izq, espacio_der,
                        kp=None):
        """Steering from the lateral sensors, with the front one allowed
        to start the corner early.

        The problem this solves: the centring error is the DIFFERENCE
        between the two sides, and approaching a corner square on, that
        difference stays small. Both walls are about equally far until
        the robot is already in the corner, so the proportional term has
        nothing to work with and the steering stays near centre. The
        robot arrives nose-first at a wall it could have seen coming
        half a metre earlier.

        The front sensor is the one that sees it. Below
        GIRO_ANTICIPADO_DISTANCIA it commands a turn of its own, towards
        whichever side has more room, growing from nothing at the
        threshold to full lock at the wall:

            closing = (threshold - frontal) / threshold
            angle   = that side's stop * closing

        The two commands do not add. Whichever asks for more steering
        wins, so on a straight the wall following is untouched, and in a
        corner the front sensor takes over exactly when it has more to
        say than the difference between the sides.
        """
        if kp is None:
            kp = config.VOLANTE_KP
        angulo = kp * error
        self.anticipando = False

        if (config.GIRO_ANTICIPADO_ACTIVO
                and frontal < config.GIRO_ANTICIPADO_DISTANCIA):
            cierre = ((config.GIRO_ANTICIPADO_DISTANCIA - frontal)
                      / float(config.GIRO_ANTICIPADO_DISTANCIA))
            # Towards the open side. Positive is right, so the right side
            # having more room asks for a positive angle.
            if espacio_der >= espacio_izq:
                anticipado = config.VOLANTE_TOPE_DERECHO * cierre
            else:
                anticipado = config.VOLANTE_TOPE_IZQUIERDO * cierre
            if abs(anticipado) > abs(angulo):
                angulo = anticipado
                self.anticipando = True

        self.girar(angulo)
        return angulo

    def describir_velocidad(self, velocidad):
        """One line saying what a speed setting means in every unit.

        Printed by both race programs at startup so that the translation
        never has to be done by hand, whichever unit VELOCIDAD_UNIDAD is
        set to. The chain is

            % of maximum -> deg/s at the motor -> cm/s on the ground

        with deg/s = % x max_speed / 100, and cm/s = deg/s / 360 / n * C.
        """
        grados = self.grados_por_segundo(velocidad)
        circunferencia_cm = math.pi * config.RUEDA_TRASERA_DIAMETRO / 10.0
        cm_s = (grados / 360.0 / config.TRACCION_REDUCCION
                * circunferencia_cm)
        porciento = grados / float(self.traccion.max_speed) * 100.0
        return ('%s %s  =  %.0f %% del motor  =  %.0f grados/s  =  %.1f cm/s'
                % (velocidad, config.VELOCIDAD_UNIDAD, porciento, grados,
                   cm_s))

    def avanzar(self, velocidad):
        """Drive forward at `velocidad`, in the unit VELOCIDAD_UNIDAD sets.

        With 'cm_s' the number is centimetres per second over the ground
        and the conversion to motor degrees is done here, so the value
        written in config is the speed the robot actually travels.

        With TRACCION_MODO = 'velocidad' the EV3 then regulates using the
        encoder: if a wheel is slowed by a bump in the track surface, the
        controller raises power until the commanded speed is recovered.

        With 'potencia' the number is the raw duty cycle and is always a
        percentage, whatever VELOCIDAD_UNIDAD says, because a duty cycle
        has no ground speed to be equal to. That mode is open loop:
        against an obstacle the power stays the same and the robot just
        stalls. Velocity mode was chosen after the robot kept bogging
        down on track imperfections.

        The command is only written when it changes. At ~44 Hz,
        rewriting identical values into sysfs every loop is wasted work.
        """
        if config.TRACCION_MODO != 'velocidad':
            velocidad = clamp_abs(velocidad, 100)
            if velocidad == self.velocidad:
                return
            self.velocidad = velocidad
            self.traccion.run_direct(duty_cycle_sp=int(round(velocidad)))
            return

        if velocidad == self.velocidad:
            return
        self.velocidad = velocidad

        grados = self.grados_por_segundo(velocidad)
        tope = self.traccion.max_speed

        # Saturation is reported, not swallowed. Asking for more than the
        # motor can turn is the one case where the number in config stops
        # being the speed on the floor, so it says so instead of quietly
        # running slower than requested.
        if abs(grados) > tope and not self._aviso_saturacion:
            self._aviso_saturacion = True
            print('AVISO: se pidio %.1f y el maximo de este robot es %.1f. '
                  'Va a ir a %.1f, no a lo pedido.'
                  % (velocidad, self.velocidad_maxima(),
                     self.velocidad_maxima()))

        self.traccion.speed_sp = int(round(clamp_abs(grados, tope)))
        self.traccion.run_forever()

    def retroceder(self, vueltas=None, velocidad=None, mientras=None):
        """Back off a fixed distance, then stop. Blocks until done.

        Used by the front collision guard. `vueltas` is turns of the
        rear WHEEL; the reduction converts it to motor degrees, so the
        distance on the ground does not change if the gearing does.

        `mientras` is called repeatedly while the robot reverses. The
        gyroscope integrates the time since its previous call, so
        leaving it untouched through a manoeuvre of a second or more
        would make the next reading arrive with a dt spanning the whole
        retreat. Passing giro.actualizar keeps the heading honest
        throughout, including the part of the turn the retreat itself
        causes.

        The steering is centred first. Reversing with the wheels at full
        lock swings the tail instead of backing straight out of whatever
        was ahead.
        """
        if vueltas is None:
            vueltas = config.PRECAUCION_VUELTAS
        if velocidad is None:
            velocidad = config.PRECAUCION_VELOCIDAD

        self.girar(0)

        grados_motor = abs(int(round(vueltas * 360.0
                                     * config.TRACCION_REDUCCION)))
        rapidez = abs(velocidad) / 100.0 * self.traccion.max_speed

        partida = self.traccion.position

        self.traccion.speed_sp = int(round(rapidez))
        self.traccion.position_sp = -grados_motor
        self.traccion.run_to_rel_pos()

        # Waiting is on the ENCODER, not on the motor's state string.
        #
        # The obvious version of this loop breaks as soon as 'running' is
        # missing from the state, and the state does not become 'running'
        # the instant the command is written: it takes a few
        # milliseconds. The loop then exited immediately, the stop below
        # cancelled the manoeuvre before the wheel had turned, and the
        # robot never moved. On track that showed up as the guard firing
        # eighteen times with the distance ahead never changing.
        #
        # The encoder cannot lie about this: either the wheel has turned
        # the requested amount or it has not.
        limite = time.time() + config.PRECAUCION_TIEMPO_MAXIMO
        tolerancia = 5          # degrees, the position controller's slop
        while time.time() < limite:
            if abs(self.traccion.position - partida) >= grados_motor - tolerancia:
                break
            if mientras is not None:
                mientras()
            time.sleep(0.02)

        self.recorrido_retroceso = abs(self.traccion.position - partida)
        self.traccion.stop(stop_action='brake')

        # Not 0.0. avanzar() skips writing a speed equal to the one it
        # last wrote, and the motor has just been stopped behind its
        # back, so leaving the cached value in place would make the next
        # avanzar() a no-op and the robot would stay parked. None never
        # compares equal to a real speed, which forces the rewrite.
        self.velocidad = None

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
