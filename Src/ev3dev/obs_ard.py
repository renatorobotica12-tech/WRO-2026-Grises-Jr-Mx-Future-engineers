#!/usr/bin/env python3
"""Obstacle challenge: three laps, avoiding coloured pillars.

The open challenge loop plus the camera:

    HuskyLens sees a block -> steer around it, to the side its colour
                              calls for
    it sees nothing        -> centre between the walls using the
                              ultrasonic sensors, as in the open run

Corner counting and the end-of-race logic are identical to open_ard.py.

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
    camara = HuskyLens()

    camara.actualizar()
    print('HuskyLens: %s' % camara.diagnostico())
    if camara.estado in (0, 8, 9):
        print('La camara no esta lista. Revise el cable y los objetos')
        print('aprendidos antes de correr.')

    print('No mueva el robot durante la calibracion.')
    offset = giro.calibrar(mostrar=lambda h, t: print('calibrando %d/%d' % (h, t)))
    print('offset del giroscopio: %.2f' % offset)
    print()

    # The EFFECTIVE values, read from config right now. Without this
    # there is no way to tell whether an edited config actually reached
    # the brick, nor which of the two speeds is in play: obs_ard uses
    # VELOCIDAD_OBSTACULOS and open_ard uses VELOCIDAD, and confusing
    # them makes a change look like it "did nothing".
    print('--- valores en uso ---')
    print('VELOCIDAD_OBSTACULOS  : %s'
          % robot.describir_velocidad(config.VELOCIDAD_OBSTACULOS))
    print('                        (no VELOCIDAD)')
    if config.TRACCION_REDUCCION == 1.0:
        print('  ojo                  : los cm/s suponen toma directa;'
              ' corra check_hw.py reduccion')
    print('VOLANTE_KP_OBSTACULOS : %s' % config.VOLANTE_KP_OBSTACULOS)
    print('guardia frontal       : %s a %d cm, solo sin bloque a la vista'
          % ('ACTIVO' if config.PRECAUCION_ACTIVA_OBSTACULOS else 'apagado',
             config.PRECAUCION_DISTANCIA_OBSTACULOS))
    print('TOPES                 : izquierda %+.1f  centro 0  derecha %+.1f'
          % (config.VOLANTE_TOPE_IZQUIERDO, config.VOLANTE_TOPE_DERECHO))
    print('camara: ROJO id %d target %+d / VERDE id %d target %+d'
          % (config.HUSKY_ID_ROJO, config.HUSKY_TARGET_ROJO,
             config.HUSKY_ID_VERDE, config.HUSKY_TARGET_VERDE))
    print('retencion %.2f s, margen de ancho %.2f, invertir X %s'
          % (config.HUSKY_RETENCION, config.HUSKY_MARGEN_ANCHO,
             config.HUSKY_INVERTIR_X))
    print()

    esperar_boton(boton, sonido)

    correr(robot, hub, giro, camara, boton, sonido)


def correr(robot, hub, giro, camara, boton, sonido):
    """The race itself, on hardware somebody else set up.

    Split out from main() so the run can be started from another
    program with the robot already prepared -- salida.py chains
    straight into it once it is out of the parking bay, and a second
    steering calibration and a second button press between the two
    would make no sense there.

    Everything before this point in main() is preparation that only
    needs doing once: finding the steering centre, calibrating the
    gyroscope, and waiting for the start button.
    """
    # The angle is zeroed at START, not at calibration time. A long wait
    # can pass between the two while the button is pressed, and any gyro
    # drift or nudge of the robot during that wait would add to the first
    # corner and trigger it early. Coming from salida.py the gap is not a
    # wait but a whole manoeuvre, which makes this more necessary rather
    # than less.
    giro.reiniciar()

    esquinas = 0
    velocidad = 0.0
    terminado = False
    ultimo_aviso = 0.0
    vueltas = 0
    vistos = 0
    retenidas = 0
    retrocesos = 0
    seguidos = 0
    guardia_activo = config.PRECAUCION_ACTIVA_OBSTACULOS
    inicio = time.time()

    try:
        while not terminado and not boton.backspace:
            inicio_vuelta = time.time()

            # 1. Sensors. One reading of each per control loop. Reading
            #    any of them twice in the same iteration buys nothing:
            #    the values cannot change between two calls that are
            #    microseconds apart.
            camara.actualizar()
            hub.actualizar()
            angulo = giro.actualizar()

            # The camera's verdict is needed before the guard can decide
            # anything, so it is read here rather than at step 4 where it
            # is used. One call either way.
            angulo_camara = camara.angulo_esquive_retenido()

            # 1b. Front collision guard, and the condition that makes it
            #     usable in this run: it only looks while the camera is
            #     NOT commanding.
            #
            #     The two would otherwise fight. Going round a block, the
            #     thing filling the front sensor IS the block, and closing
            #     on it is the whole manoeuvre; a guard would reverse out
            #     of it and the camera would drive back in, taking turns
            #     undoing each other until the run ended.
            #
            #     With the camera silent, a wall ahead is what it looks
            #     like: the same failure as in the open challenge, where
            #     the difference between the two sides goes to zero
            #     square on to a wall and the controller reports that all
            #     is well.
            if (guardia_activo
                    and angulo_camara is None
                    and hub.frontal < config.PRECAUCION_DISTANCIA_OBSTACULOS):
                antes = hub.frontal
                retrocesos += 1
                robot.retroceder(mientras=giro.actualizar)
                hub.actualizar()
                print('PRECAUCION: %.0f cm al frente sin bloque a la vista, '
                      'retrocedio %d grados, ahora %.0f cm'
                      % (antes, robot.recorrido_retroceso, hub.frontal))

                if hub.frontal <= antes + 1:
                    seguidos += 1
                    if seguidos >= config.PRECAUCION_MAXIMOS_SEGUIDOS:
                        guardia_activo = False
                        print('PRECAUCION: %d retrocesos seguidos sin que se '
                              'despeje. Guardia APAGADO para esta corrida.'
                              % seguidos)
                else:
                    seguidos = 0
                continue

            # 2. Corner counting. es_esquina() discards the false ones:
            #    while avoiding a block the steering goes to full lock
            #    and the accumulated turn passes the threshold without
            #    there being a track corner at all. See imu.py.
            if giro.es_esquina():
                esquinas += 1
                print('esquina %d' % esquinas)

            if esquinas >= config.ESQUINAS_META:
                limite = time.time() + config.MS_EXTRA_AL_FINAL_OBS / 1000.0
                while time.time() < limite:
                    hub.actualizar()
                    robot.avanzar(velocidad)
                    robot.girar_por_error(hub.error_crudo(),
                                      config.VOLANTE_KP_OBSTACULOS)
                    time.sleep(0.01)
                velocidad = 0.0
                terminado = True
            else:
                velocidad = config.VELOCIDAD_OBSTACULOS

            # 3. Drive train.
            robot.avanzar(velocidad)

            # 4. Steering: the camera commands it when it sees a block,
            #    otherwise the ultrasonic sensors do. The held version is
            #    used: it rides out one- or two-frame dropouts and the
            #    adapter switching between two blocks in view. Without
            #    it, every isolated dropout handed control back to wall
            #    following, which at that instant sent the steering to
            #    full lock. See husky.py. Already read at step 1.
            if angulo_camara is not None:
                vistos += 1
                robot.girar(angulo_camara)
                if camara.reteniendo:
                    retenidas += 1
                    # The camera's current readings do not describe the
                    # command being executed, so they are not printed.
                    modo = ('CAM* reteniendo %+5.1f  pasa por la %s'
                            % (angulo_camara,
                               'DERECHA' if angulo_camara > 0
                               else 'IZQUIERDA'))
                else:
                    modo = ('CAM  %s x=%+4.0f target=%+4d w=%3d -> %+5.1f'
                            '  pasa por la %s'
                            % (camara.color, camara.x, camara.target(),
                               camara.ancho, angulo_camara,
                               'DERECHA' if angulo_camara > 0
                               else 'IZQUIERDA'))
            else:
                robot.girar_por_error(hub.error_crudo(),
                                      config.VOLANTE_KP_OBSTACULOS)
                modo = 'DIS error=%+5.1f -> %+5.1f' % (
                    hub.error_crudo(), robot.angulo_volante)

            robot.indicar_vuelta(esquinas)

            vueltas += 1
            ahora = time.time()
            if (config.OBS_TELEMETRIA
                    and ahora - ultimo_aviso >= 1.0 / config.OBS_TELEMETRIA_HZ):
                ultimo_aviso = ahora
                # The gyro angle goes into the telemetry because it is
                # the only thing that shows why a corner was counted, or
                # was not: without it, an odd count cannot be diagnosed
                # once the race is over.
                print('%5.1f  esq=%2d  giro=%+6.1f  %s'
                      % (ahora - inicio, esquinas, angulo, modo))

            resto = config.PERIODO_LAZO - (time.time() - inicio_vuelta)
            if resto > 0:
                time.sleep(resto)
    finally:
        robot.apagar()
        hub.cerrar()

    duracion = time.time() - inicio
    print()
    print('esquinas contadas: %d de %d en %.1f s'
          % (esquinas, config.ESQUINAS_META, duracion))
    print('esquinas falsas descartadas: %d' % giro.esquinas_descartadas)
    print('%d vueltas de lazo = %.0f Hz'
          % (vueltas, vueltas / duracion if duracion else 0))
    print('vueltas con mando de camara: %d de %d  (de ellas %d retenidas)'
          % (vistos, vueltas, retenidas))
    print('tramas malas del Nano: %d de %d'
          % (hub.tramas_malas, hub.tramas_leidas))
    print('lecturas sin eco sustituidas, por sensor: %s' % hub.sin_eco)
    print('de esas, estimadas de la pareja del lado   : %s' % hub.estimados)
    print('frontal sostenido por prudencia            : %d' % hub.pesimistas)
    if not config.PRECAUCION_ACTIVA_OBSTACULOS:
        nota = '  (guardia OFF)'
    elif not guardia_activo:
        nota = '  (guardia se APAGO solo)'
    else:
        nota = ''
    print('retrocesos de precaucion: %d%s' % (retrocesos, nota))
    sonido.beep()


if __name__ == '__main__':
    main()
