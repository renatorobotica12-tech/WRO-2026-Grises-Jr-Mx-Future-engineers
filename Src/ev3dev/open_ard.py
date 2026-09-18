#!/usr/bin/env python3
"""Open challenge: three laps, walls only, no camera.

The control loop each iteration:

    read gyro -> read distances -> drive -> steer ->
    count corners -> once 12 are counted, run on briefly and stop

Twelve corners is three laps of a four-corner track.

Press the brick's back button to stop the robot at any time.
"""

import os
import sys
import time

from ev3dev2.button import Button
from ev3dev2.sound import Sound

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wro import config
from wro.imu import Giroscopio
from wro.robot import Robot
from wro.ultrasonics import crear_hub


def esperar_boton(boton, sonido):
    print('Listo. Pulse el boton central para arrancar.')
    sonido.beep()
    while not boton.enter:
        time.sleep(0.05)
    while boton.enter:
        time.sleep(0.05)


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

    def progreso(hecho, total):
        print('calibrando %d/%d' % (hecho, total))

    print('No mueva el robot durante la calibracion.')
    offset = giro.calibrar(mostrar=progreso)
    print('offset del giroscopio: %.2f' % offset)
    print()

    # The EFFECTIVE values, read from config right now. Without this
    # there is no way to tell from outside whether an edited config
    # actually reached the brick, nor which of the two speeds is in play:
    # open_ard uses VELOCIDAD and obs_ard uses VELOCIDAD_OBSTACULOS, and
    # confusing them makes a change look like it "did nothing".
    print('--- valores en uso ---')
    print('VELOCIDAD      : %s' % robot.describir_velocidad(config.VELOCIDAD))
    print('                 (VELOCIDAD, no VELOCIDAD_OBSTACULOS)')
    if config.TRACCION_REDUCCION == 1.0:
        print('  ojo           : los cm/s suponen toma directa;'
              ' corra check_hw.py reduccion')
    print('VOLANTE_KP     : %s   satura con error %.1f'
          % (config.VOLANTE_KP, config.VOLANTE_ERROR_TOPE))
    print('TOPES          : izquierda %+.1f  centro 0  derecha %+.1f'
          % (config.VOLANTE_TOPE_IZQUIERDO, config.VOLANTE_TOPE_DERECHO))
    print()

    esperar_boton(boton, sonido)

    # The angle is zeroed at START, not at calibration time. A long wait
    # can pass between the two while the button is pressed, and any gyro
    # drift or nudge of the robot during that wait would add to the first
    # corner and trigger it early. Same reason as in obs_ard.py.
    giro.reiniciar()

    esquinas = 0
    velocidad = 0.0
    terminado = False
    retrocesos = 0
    seguidos = 0
    anticipados = 0
    guardia_activo = config.PRECAUCION_ACTIVA

    try:
        while not terminado and not boton.backspace:
            inicio_vuelta = time.time()

            # 1. Gyroscope. One reading per control loop.
            angulo = giro.actualizar()

            # 2. Distances and control. The drive motor is given the
            #    speed computed on the previous iteration, so that a
            #    corner detected this iteration stops the robot without
            #    one last burst of throttle.
            hub.actualizar()

            # 2b. Front collision guard. The centring error is the
            #     DIFFERENCE between the two sides, and square on to a
            #     wall that difference is zero: the controller reports
            #     that all is well while the robot drives into it. The
            #     front sensor is the only one that sees this, so it
            #     gets a veto over the lap.
            #
            #     giro.actualizar is handed over so the heading keeps
            #     integrating through the manoeuvre instead of arriving
            #     afterwards with a dt spanning the whole retreat.
            if (guardia_activo
                    and hub.frontal < config.PRECAUCION_DISTANCIA):
                antes = hub.frontal
                retrocesos += 1
                robot.retroceder(mientras=giro.actualizar)
                hub.actualizar()
                print('PRECAUCION: %.0f cm al frente, retrocedio %d grados, '
                      'ahora %.0f cm'
                      % (antes, robot.recorrido_retroceso, hub.frontal))

                # A retreat that does not open up the space in front of
                # the robot has not fixed anything, and doing it again
                # will not either. Counting only the ones that failed to
                # help is what separates "a tight corner took two goes"
                # from "this sensor is never going to clear".
                if hub.frontal <= antes + 1:
                    seguidos += 1
                    if seguidos >= config.PRECAUCION_MAXIMOS_SEGUIDOS:
                        guardia_activo = False
                        print('PRECAUCION: %d retrocesos seguidos sin que se '
                              'despeje el frente. Algo fijo lo esta tapando, '
                              'o IDX_FRONTAL no es el sensor de enfrente.'
                              % seguidos)
                        print('PRECAUCION: guardia APAGADO para esta corrida. '
                              'Revise con check_hw.py ultra y mapear.')
                else:
                    seguidos = 0
                continue

            robot.avanzar(velocidad)
            robot.girar_por_pared(hub.error_crudo(), hub.frontal,
                                  sum(hub.izquierda), sum(hub.derecha))
            if robot.anticipando:
                anticipados += 1

            # 3. Corner counting by accumulated turn. The threshold, the
            #    angle reset and the discarding of false corners all live
            #    inside es_esquina(); see imu.py.
            if giro.es_esquina():
                esquinas += 1
                print('esquina %d' % esquinas)

            # 4. End of the three laps. The robot keeps going a little
            #    longer so it finishes inside the start zone rather than
            #    braking the moment it clears the last corner. It is
            #    still following the walls during that run-on, not
            #    driving blind.
            if esquinas >= config.ESQUINAS_META:
                limite = time.time() + config.MS_EXTRA_AL_FINAL / 1000.0
                while time.time() < limite:
                    hub.actualizar()
                    robot.avanzar(velocidad)
                    robot.girar_por_error(hub.error_crudo())
                    time.sleep(0.01)
                velocidad = 0.0
                terminado = True
            else:
                velocidad = config.VELOCIDAD

            robot.indicar_vuelta(esquinas)

            # The loop is capped at PERIODO_LAZO. If reading the sensors
            # already took longer than that, nothing is slept.
            resto = config.PERIODO_LAZO - (time.time() - inicio_vuelta)
            if resto > 0:
                time.sleep(resto)
    finally:
        robot.apagar()
        hub.cerrar()

    print('esquinas: %d  tramas malas: %d de %d'
          % (esquinas, hub.tramas_malas, hub.tramas_leidas))
    # More than one or two means the robot is arriving at the corners
    # too square to turn out of them, which is a steering problem the
    # guard is only papering over. Look at VOLANTE_KP and the speed.
    print('retrocesos de precaucion: %d%s'
          % (retrocesos, '' if guardia_activo else '  (guardia se APAGO solo)'))
    # The two numbers read together. Corners started early should be a
    # healthy fraction of the loop; retreats should be zero. Retreats
    # with no anticipation means the threshold is too close.
    print('vueltas de lazo con giro anticipado: %d' % anticipados)
    sonido.beep()


if __name__ == '__main__':
    main()
