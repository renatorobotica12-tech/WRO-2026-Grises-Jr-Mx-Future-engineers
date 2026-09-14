#!/usr/bin/env python3
"""OBS_ARD en ev3dev: prueba de obstaculos, tres vueltas.

Replica del programa `WRO OBS ARD-UNO.mp` de Arath. Es el mismo lazo de
la prueba abierta mas la camara:

    si la HuskyLens ve un bloque -> el volante lo esquiva por el lado
    que corresponde a su color
    si no ve nada               -> el volante se centra entre paredes
    con los ultrasonicos, igual que en la prueba abierta

El conteo de esquinas y el final de carrera vienen del procedimiento
`3 vueltas` del original y son identicos a los de open_ard.py.

Para detener el robot en cualquier momento, el boton de retroceso.
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

    # Valores EFECTIVOS, leidos de config en este momento. Sin esto no hay
    # forma de saber si el config que se edito llego al ladrillo, ni cual
    # de las dos velocidades esta en juego: obs_ard usa
    # VELOCIDAD_OBSTACULOS y open_ard usa VELOCIDAD, y confundirlas parece
    # que el cambio "no hizo nada".
    print('--- valores en uso ---')
    print('VELOCIDAD_OBSTACULOS  : %s   (no VELOCIDAD)'
          % config.VELOCIDAD_OBSTACULOS)
    print('VOLANTE_KP_OBSTACULOS : %s' % config.VOLANTE_KP_OBSTACULOS)
    print('VOLANTE_LIMITE        : %.1f  (derecha %+.1f, izquierda %+.1f)'
          % (config.VOLANTE_LIMITE,
             config.VOLANTE_LIMITE * config.VOLANTE_FRACCION_DERECHA,
             -config.VOLANTE_LIMITE * config.VOLANTE_FRACCION_IZQUIERDA))
    print('camara: ROJO id %d target %+d / VERDE id %d target %+d'
          % (config.HUSKY_ID_ROJO, config.HUSKY_TARGET_ROJO,
             config.HUSKY_ID_VERDE, config.HUSKY_TARGET_VERDE))
    print('retencion %.2f s, margen de ancho %.2f, invertir X %s'
          % (config.HUSKY_RETENCION, config.HUSKY_MARGEN_ANCHO,
             config.HUSKY_INVERTIR_X))
    print()

    esperar_boton(boton, sonido)

    # El angulo se pone a cero al ARRANCAR, no al calibrar. Entre una cosa
    # y otra puede pasar un rato largo esperando el boton, y cualquier
    # deriva del giroscopio o empujon del robot en esa espera se sumaria a
    # la primera esquina, adelantandola.
    giro.reiniciar()

    esquinas = 0
    velocidad = 0.0
    terminado = False
    ultimo_aviso = 0.0
    vueltas = 0
    vistos = 0
    retenidas = 0
    inicio = time.time()

    try:
        while not terminado and not boton.backspace:
            inicio_vuelta = time.time()

            # 1. Sensores. Una lectura de cada uno por vuelta de lazo.
            #    El original llama a `actualizar Huskylens` tres veces y a
            #    `Actualizar Distancia` dos; es ruido de programacion por
            #    bloques, no hace falta repetirlas.
            camara.actualizar()
            hub.actualizar()
            angulo = giro.actualizar()

            # 2. Conteo de esquinas, del procedimiento `3 vueltas`.
            #    es_esquina() descarta las falsas: esquivando un bloque el
            #    volante va al tope y el giro acumulado pasa el umbral sin
            #    que haya esquina de pista. Ver imu.py.
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

            # 3. Traccion.
            robot.avanzar(velocidad)

            # 4. Volante: manda la camara si ve algo, si no los ultrasonicos.
            #    Se usa la version con retencion: aguanta los parpadeos de
            #    una o dos tramas y el alternado del adaptador cuando hay
            #    dos bloques a la vista. Sin ella, cada fallo suelto
            #    devolvia el mando al seguimiento de pared, que en ese
            #    instante mandaba el volante al tope. Ver husky.py.
            angulo_camara = camara.angulo_esquive_retenido()

            if angulo_camara is not None:
                vistos += 1
                robot.girar(angulo_camara)
                if camara.reteniendo:
                    retenidas += 1
                    # Los datos actuales de la camara no describen la orden
                    # que se esta ejecutando, asi que no se imprimen.
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
                # El angulo del giroscopio va en la telemetria porque es lo
                # unico que deja ver por que se conto (o no se conto) una
                # esquina: sin el, un conteo raro no se puede diagnosticar
                # despues de la carrera.
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
    sonido.beep()


if __name__ == '__main__':
    main()
