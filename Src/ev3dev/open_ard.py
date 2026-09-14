#!/usr/bin/env python3
"""OPEN_ARD en ev3dev: prueba abierta, tres vueltas.

Replica del programa `WRO OPEN ARD-UNO.mp` de Arath sobre el hardware de
Renato. La estructura del lazo es la misma del original:

    actualizar IMU -> leer distancias -> motor -> volante ->
    contar esquinas -> si van 12, avanzar 200 ms mas y frenar

Para detener el robot en cualquier momento, el boton de retroceso.
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

    # Se imprimen los valores EFECTIVOS, leidos de config en este momento.
    # Sin esto no hay forma de saber desde fuera si el config que se edito
    # llego al ladrillo, ni cual de las dos velocidades esta en juego:
    # open_ard usa VELOCIDAD y obs_ard usa VELOCIDAD_OBSTACULOS, y
    # confundirlas parece que el cambio "no hizo nada".
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

            # 1. Giroscopio. Una sola lectura por vuelta de lazo.
            angulo = giro.actualizar()

            # 2. Distancias y control. En el original el motor recibe la
            #    velocidad de la vuelta anterior; se respeta ese orden.
            hub.actualizar()
            robot.avanzar(velocidad)
            robot.girar_por_error(hub.error_crudo())

            # 3. Conteo de esquinas por giro acumulado. El umbral, el
            #    reinicio del angulo y el descarte de esquinas falsas
            #    estan dentro de es_esquina(); ver imu.py.
            if giro.es_esquina():
                esquinas += 1
                print('esquina %d' % esquinas)

            # 4. Fin de las tres vueltas.
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

            # El lazo se limita a PERIODO_LAZO; si el I2C ya tardo mas,
            # no se duerme nada.
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
