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
    print('VELOCIDAD      : %s   (VELOCIDAD, no VELOCIDAD_OBSTACULOS)'
          % config.VELOCIDAD)
    print('VOLANTE_KP     : %s   satura con error %.1f'
          % (config.VOLANTE_KP, config.VOLANTE_ERROR_TOPE))
    print('VOLANTE_LIMITE : %.1f  (derecha %+.1f, izquierda %+.1f)'
          % (config.VOLANTE_LIMITE,
             config.VOLANTE_LIMITE * config.VOLANTE_FRACCION_DERECHA,
             -config.VOLANTE_LIMITE * config.VOLANTE_FRACCION_IZQUIERDA))
    print()

    esperar_boton(boton, sonido)

    esquinas = 0
    velocidad = 0.0
    terminado = False

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
            robot.avanzar(velocidad)
            robot.girar_por_error(hub.error_crudo())

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
    sonido.beep()


if __name__ == '__main__':
    main()
