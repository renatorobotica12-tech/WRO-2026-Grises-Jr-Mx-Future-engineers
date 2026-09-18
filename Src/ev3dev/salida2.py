#!/usr/bin/env python3
"""Parking exit, the other way: back off, turn hard, drive out.

A second manoeuvre, kept beside salida.py rather than replacing it.
Three steps and no repetition:

    1. reverse SALIDA2_RETROCESO_CM, steering centred
    2. wheels to the stop on the SALIDA2_LADO side
    3. hold it there and drive forward for SALIDA2_SALIR_SEGUNDOS

Where salida.py rocks back and forth, gaining angle a pass at a time,
this one commits: back off far enough to have room, put the wheels on
the stop, and leave in a single arc. It wants a bay the robot already
sits roughly square in. The other one is for the bay that has to be
worked out of.

The two share their parts. The exit test, the confirmation window and
the encoder helper all come from salida.py, so a fix to how "out" is
decided lands in both and cannot drift between them.

There is no rear sensor. The reverse watches the encoder instead: wheels
that stop turning while the motor is still driving them mean there is a
wall behind, and the phase is cut short rather than spent pushing.

Press the brick's back button to stop the robot at any time.
"""

import os
import sys
import time

from ev3dev2.button import Button
from ev3dev2.sound import Sound

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wro import config
from wro.husky import HuskyLens
from wro.imu import Giroscopio
from wro.robot import Robot
from wro.ultrasonics import crear_hub

from salida import confirmar_fuera, esperar_boton, vueltas_recorridas


def fase_retroceder(robot, giro, boton):
    """Step 1: straight back SALIDA2_RETROCESO_CM, on the encoder.

    A distance rather than a duration, for the same reason as in
    salida.py: timed, the drive train delivered 57 % of what it was
    asked for when reversing, and no amount of adjusting seconds fixes
    a number that depends on friction.

    Steering centred. This is meant to buy room, not to change where the
    robot points; the turn comes after.
    """
    circunferencia = 3.1416 * config.RUEDA_TRASERA_DIAMETRO / 10.0

    print()
    print('--- 1. retrocediendo %.1f cm, volante recto ---'
          % config.SALIDA2_RETROCESO_CM)

    robot.girar(0)
    time.sleep(0.6)

    giro.reiniciar()
    partida = robot.traccion.position
    limite = time.time() + config.SALIDA_RETROCESO_TIEMPO_MAXIMO
    motivo = 'se acabo el tiempo'
    atascado = False

    robot.avanzar(-config.SALIDA2_VELOCIDAD_RETROCESO)

    # Standing in for the rear sensor that does not exist. Wheels held
    # still while the motor is being told to turn them mean the robot is
    # against something; speed regulation makes that sharper, since the
    # controller raises power to hold the commanded speed.
    # Not from now: the motor needs a moment to come up to speed, and
    # during it a starting wheel and a stalled one look the same. A run
    # reported "atascado: 0.34 cm de 10.0" with nothing behind the robot
    # because of exactly that.
    marca = time.time() + config.SALIDA_ATASCO_GRACIA
    posicion_marca = partida

    while time.time() < limite and not boton.backspace:
        giro.actualizar()

        if (vueltas_recorridas(robot, partida) * circunferencia
                >= config.SALIDA2_RETROCESO_CM):
            motivo = 'distancia completada'
            break

        ahora = time.time()
        if ahora - marca >= config.SALIDA_ATASCO_VENTANA:
            if (abs(robot.traccion.position - posicion_marca)
                    < config.SALIDA_ATASCO_GRADOS):
                atascado = True
                motivo = 'atascado'
                break
            marca = ahora
            posicion_marca = robot.traccion.position

        time.sleep(0.01)

    robot.frenar()

    recorrido = vueltas_recorridas(robot, partida) * circunferencia
    print('    parado por %s: %.2f cm de %.1f, giro %+.1f'
          % (motivo, recorrido, config.SALIDA2_RETROCESO_CM, giro.grados))
    if atascado:
        print('    Las ruedas dejaron de girar con el motor mandando: hay')
        print('    algo detras. Se sale desde donde quedo.')
    return motivo


def fase_salir(robot, hub, giro, boton):
    """Steps 2 and 3: wheels on the stop, and out.

    One committed arc. The wheels go to SALIDA2_TOPE, stay there, and
    the robot drives forward for SALIDA2_SALIR_SEGUNDOS.

    They go over first and are given time to arrive: driving off while
    they are still swinging spends the opening centimetres on a curve
    nobody asked for, and those are the centimetres nearest the wall.

    Timed rather than watched. How far the arc got the robot is a
    question for the exit test afterwards; the front sensor's veto is
    the only thing that ends it early.
    """
    izquierda = config.SALIDA2_LADO == 'izquierda'
    tope = -config.SALIDA2_TOPE if izquierda else config.SALIDA2_TOPE

    # The declared stops are widened for the length of this arc, and put
    # back afterwards.
    #
    # Robot.girar() clamps every steering command against
    # VOLANTE_TOPE_*, and it has to keep being the single point that
    # does: the wall following, the camera avoidance and this all pass
    # through it. So rather than adding a way around the clamp, the
    # clamp itself is moved, for one phase, and restored in the finally
    # below however the phase ends.
    #
    # Why bother: VOLANTE_TOPE_* is 30 a side, and that 30 is a policy
    # chosen for the races -- a gentler line through corners. Getting
    # out of a bay wants the opposite, the tightest arc the linkage can
    # make, which is the measured 50.6.
    tope_izq = config.VOLANTE_TOPE_IZQUIERDO
    tope_der = config.VOLANTE_TOPE_DERECHO
    config.VOLANTE_TOPE_IZQUIERDO = -config.SALIDA2_TOPE
    config.VOLANTE_TOPE_DERECHO = config.SALIDA2_TOPE

    print()
    print('--- 2. volante al tope %s (%+.1f) y adelante %s s a %s ---'
          % (config.SALIDA2_LADO.upper(), tope,
             config.SALIDA2_SALIR_SEGUNDOS, config.SALIDA2_VELOCIDAD_SALIDA))

    try:
        robot.girar(tope)
        time.sleep(0.6)
        print('    volante en %+.1f' % robot.angulo_volante)

        giro.reiniciar()
        partida = robot.traccion.position
        limite = time.time() + config.SALIDA2_SALIR_SEGUNDOS
        motivo = 'arco completado'

        # The wall the robot ALREADY has in front does not count.
        #
        # A veto that only looked at the distance killed the arc on its
        # first pass: "parado por pared al frente, frente 3", 0.12 turns
        # in, before the manoeuvre had begun. That wall was not in the
        # way of the arc; it was the thing the arc goes around.
        #
        # So the veto asks whether the front is getting CLOSER than it
        # was at the start. A wall that was there and stays, or falls
        # away as the robot turns, is expected. One that closes in is
        # something the arc is driving into.
        hub.actualizar()
        frente_inicial = hub.frontal

        # A duration, not a condition. This manoeuvre is one committed
        # arc rather than a search: the wheels are over, the robot goes
        # round, and how far that got it is a question for the exit test
        # afterwards rather than something the phase watches for.
        while time.time() < limite and not boton.backspace:
            hub.actualizar()
            giro.actualizar()

            if (hub.frontal <= config.SALIDA_FRENTE_MINIMO
                    and hub.frontal < frente_inicial):
                motivo = 'pared acercandose al frente'
                break

            robot.avanzar(config.SALIDA2_VELOCIDAD_SALIDA)
            time.sleep(0.02)
        else:
            if boton.backspace:
                motivo = 'boton de retroceso'

        robot.frenar()
        print('    parado por %s: %.2f vueltas, giro %+.1f, frente %.0f, '
              'der %.0f'
              % (motivo, vueltas_recorridas(robot, partida), giro.grados,
                 hub.frontal, min(hub.derecha)))
    finally:
        # Centre the wheels while the wider stop is still in force, then
        # put the declared stops back. In the other order the steering
        # would be centred under limits that no longer allow where it
        # currently is.
        robot.girar(0)
        config.VOLANTE_TOPE_IZQUIERDO = tope_izq
        config.VOLANTE_TOPE_DERECHO = tope_der

    return motivo


def main():
    boton = Button()
    sonido = Sound()

    robot = Robot()
    print('calibrando el volante contra los topes...')
    robot.preparar_volante()
    print(robot.resumen_topes())
    print()

    hub = crear_hub()
    giro = Giroscopio()

    print('No mueva el robot durante la calibracion.')
    offset = giro.calibrar(
        mostrar=lambda h, t: print('calibrando %d/%d' % (h, t)))
    print('offset del giroscopio: %.2f' % offset)
    print()

    print('--- valores en uso ---')
    print('retroceso : %.1f cm a %s %%'
          % (config.SALIDA2_RETROCESO_CM, config.SALIDA2_VELOCIDAD_RETROCESO))
    print('arco      : tope %s, %s'
          % (config.SALIDA2_LADO,
             robot.describir_velocidad(config.SALIDA2_VELOCIDAD_SALIDA)))
    print('fuera si  : frente >= %d y derecha >= %d'
          % (config.SALIDA_LIBRE, config.SALIDA_LIBRE_DERECHA))
    print()
    print('NO hay sensor trasero. El retroceso vigila el encoder, pero')
    print('despeje lo que haya detras del robot.')
    print()

    esperar_boton(boton, sonido)

    inicio = time.time()
    fuera = False

    try:
        fase_retroceder(robot, giro, boton)
        if boton.backspace:
            return

        motivo = fase_salir(robot, hub, giro, boton)
        if boton.backspace:
            return

        # Confirmed over a window, not taken from the instant the arc
        # ended. The robot has been turning, so the front sensor sweeps
        # the scene and any gap reads as open for a frame.
        fuera, frente, izq, der, via = confirmar_fuera(hub, boton)
        print()
        print('frente %.0f, izquierda %.0f, derecha %.0f  ->  %s'
              % (frente, izq, der, 'FUERA' if fuera else 'todavia no'))

        if not fuera:
            print()
            print('No quedo fuera. Hacen falta frente >= %d y derecha >= %d.'
                  % (config.SALIDA_LIBRE, config.SALIDA_LIBRE_DERECHA))
            print('Esta maniobra no reintenta: es de una pasada. Para un')
            print('hueco que necesita varias, use salida.py.')

        elif config.SALIDA_SEGUIR_CON_OBSTACULOS:
            print()
            print('=' * 50)
            print('  FUERA del estacionamiento: OBSTACLE CHALLENGE')
            print('=' * 50)

            import obs_ard
            camara = HuskyLens()
            camara.actualizar()
            print('HuskyLens: %s' % camara.diagnostico())
            if camara.estado in (0, 8, 9):
                print('La camara no esta lista. No se arranca la carrera.')
            else:
                obs_ard.correr(robot, hub, giro, camara, boton, sonido)
                return
    finally:
        robot.apagar()
        hub.cerrar()

    print()
    print('maniobra terminada en %.1f s, %s'
          % (time.time() - inicio, 'FUERA' if fuera else 'sin salir'))
    print('tramas malas del Nano: %d de %d, lecturas fallidas: %d'
          % (hub.tramas_malas, hub.tramas_leidas, hub.lecturas_fallidas))
    sonido.beep()


if __name__ == '__main__':
    main()
