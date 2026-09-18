#!/usr/bin/env python3
"""Parking entry: find the bay with the camera and reverse into it.

The mirror of salida.py, and not a symmetric one. Getting out of a bay
forgives anything: whatever rotation frees the robot has worked. Getting
in has to land inside a bounded box, so where the exit can move blind,
the entry has to close its loop on something it measures.

That something is the GYRO. Parallel parking is a heading reached and
then undone: swing to an angle against the wall, counter-steer, and come
out of the turn as the heading returns to zero, by which point the robot
is inside. Driving those two phases on the encoder would be guessing at
an angle; driving them on the gyro is measuring it.

    A. follow the wall until the lateral pair reports a gap AND the
       camera confirms it is the parking bay
    B. position, so the rear axle sits level with the far edge
    C. reverse at full lock until the heading has swung ENTRADA_ANGULO
    D. counter-lock, still reversing, until the heading is back to zero
    E. if not in, pull forward and go round again, up to
       ENTRADA_INTENTOS_MAXIMOS times
    F. centre up

Why the camera decides, and the ultrasonics only measure: a gap in a
wall is not a parking bay. It is also a doorway, the space between two
blocks, or a corner taken wide. The lateral pair can tell you something
is missing from the wall; only the camera can tell you WHICH something.
So the gap is measured on the encoder, as before, and then thrown away
unless the marker was in frame while the robot drove past it.

> [!IMPORTANT]
> There is NO REAR SENSOR. Phases C and D reverse towards the back of
> the bay with nothing looking that way. What stands in for it is an
> encoder ceiling per phase and the stall detector, which notices wheels
> that stop turning while the motor is still driving them. That is a
> detector, not a sensor: it registers the contact, it does not avoid
> it, and it needs about 0.9 s to be sure.
>
> Forward moves DO have a sensor, and they use it: every one of them
> watches the front ultrasonic and stops short of
> ENTRADA_FRENTE_GUARDIA_CM. The asymmetry is the hardware's, not the
> programme's.

The brick's back button stops the robot at any point.
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

from salida_libre import esperar_boton, vueltas_recorridas


def signo_lado():
    """+1 when the bay is on the right, -1 when it is on the left.

    This means what it says. It is NOT the crossed steering name that
    SALIDA_LADO carries: the entry has no reverse-then-forward pairing
    whose lock has to be read backwards.
    """
    return 1 if config.ENTRADA_LADO == 'derecha' else -1


def lateral(hub):
    """Distance on the parking side, in centimetres."""
    par = hub.derecha if config.ENTRADA_LADO == 'derecha' else hub.izquierda
    return min(par)


def ve_la_bahia(camara):
    """The parking marker is in frame, and big enough to be it.

    The width test is the lesson salida.py paid for: under changed
    lighting the camera reports a learned colour off walls, floor and
    reflections many times a run. The ID alone is not evidence.
    """
    if camara is None:
        return False
    if not (camara.hay_objeto and camara.id == config.ENTRADA_ID_BAHIA):
        return False
    return camara.ancho >= config.ENTRADA_CAMARA_ANCHO_MINIMO


def circunferencia():
    return 3.1416 * config.RUEDA_TRASERA_DIAMETRO / 10.0


def avanzar_cm(robot, hub, boton, cm, velocidad, etiqueta):
    """Forward a distance, watching the front sensor the whole way.

    The guard is the point. Everything ahead of the robot is visible, so
    a forward move that drives into something is a move that chose not
    to look. Phase B in particular runs the length of the bay and more,
    and whatever is parked past it does not move out of the way.

    Returns True when the distance was covered.
    """
    circ = circunferencia()
    partida = robot.traccion.position
    robot.avanzar(abs(velocidad))

    limite = time.time() + max(
        3.0, config.SALIDA_RETROCESO_MARGEN_TIEMPO * cm
        / (abs(velocidad) / 100.0 * 1560.0 / 360.0
           / config.TRACCION_REDUCCION * circ))
    motivo = 'se acabo el tiempo'
    completo = False

    while time.time() < limite and not boton.backspace:
        hub.actualizar()

        if vueltas_recorridas(robot, partida) * circ >= cm:
            motivo = 'completado'
            completo = True
            break

        if hub.frontal <= config.ENTRADA_FRENTE_GUARDIA_CM:
            motivo = 'ALGO DELANTE a %.0f cm' % hub.frontal
            break

        time.sleep(0.02)

    robot.frenar()
    recorrido = vueltas_recorridas(robot, partida) * circ
    print('    %-20s %.1f cm de %.1f  (%s)' % (etiqueta, recorrido, cm, motivo))
    return completo


def retroceder_cm(robot, boton, cm, velocidad, etiqueta):
    """Back a distance, on the encoder, with the stall detector."""
    circ = circunferencia()
    partida = robot.traccion.position
    robot.avanzar(-abs(velocidad))

    limite = time.time() + max(
        3.0, config.SALIDA_RETROCESO_MARGEN_TIEMPO * cm
        / (abs(velocidad) / 100.0 * 1560.0 / 360.0
           / config.TRACCION_REDUCCION * circ))
    marca = time.time() + config.SALIDA_ATASCO_GRACIA
    posicion_marca = robot.traccion.position
    motivo = 'se acabo el tiempo'

    while time.time() < limite and not boton.backspace:
        if vueltas_recorridas(robot, partida) * circ >= cm:
            motivo = 'completado'
            break
        ahora = time.time()
        if ahora - marca >= config.SALIDA_ATASCO_VENTANA:
            if (abs(robot.traccion.position - posicion_marca)
                    < config.SALIDA_ATASCO_GRADOS):
                motivo = 'ATASCADO: algo detras'
                break
            marca = ahora
            posicion_marca = robot.traccion.position
        time.sleep(0.01)

    robot.frenar()
    print('    %-20s %.1f cm de %.1f  (%s)'
          % (etiqueta, vueltas_recorridas(robot, partida) * circ, cm, motivo))
    return motivo == 'completado'


def fase_hasta_perder(robot, hub, giro, camara, boton):
    """Phase A, camera version: straight on until the marker leaves frame.

    The robot drives along the bay wall with the marker in frame, and
    the moment it goes -- and stays gone for ENTRADA_PERDIDA_CM -- it is
    level with the far edge and the manoeuvre starts.

    Two guards, and the phase is not usable without either:

    It ARMS only after a confirmed sighting. Absence means something
    only after presence; a marker that was never in frame is an empty
    corridor, not a bay just passed. Without this the robot would take
    the first metre of blank wall as its cue.

    And the absence has to HOLD over ENTRADA_PERDIDA_CM. The marker
    drops out for a frame or two on its own, and salida.py paid for that
    lesson: a rule built on absence needs a window or it fires on noise.

    Returns (disparo, visto_cm), where visto_cm is how far the robot
    travelled with the marker in sight -- a number worth watching,
    because it should be about the length of the bay wall, and if it is
    a few centimetres the camera is flickering rather than tracking.
    """
    print()
    print('--- A. recto hasta perder el marcador ID %d ---'
          % config.ENTRADA_ID_BAHIA)

    circ = circunferencia()
    partida = robot.traccion.position

    robot.girar(0)
    time.sleep(0.4)
    robot.avanzar(config.ENTRADA_VELOCIDAD_BUSQUEDA)

    armado = False
    primer_visto = None
    ultimo_visto = 0.0
    perdido_desde = None
    disparo = False

    while not boton.backspace:
        hub.actualizar()
        giro.actualizar()
        if camara is not None:
            camara.actualizar()
        recorrido = vueltas_recorridas(robot, partida) * circ

        if recorrido > config.ENTRADA_BUSQUEDA_MAXIMA_CM:
            print('    %.0f cm sin disparar. Se para.' % recorrido)
            break

        if hub.frontal <= config.ENTRADA_FRENTE_GUARDIA_CM:
            print('    algo delante a %.0f cm. Se para.' % hub.frontal)
            break

        if ve_la_bahia(camara):
            if not armado:
                armado = True
                primer_visto = recorrido
                print('    marcador a la vista a los %.0f cm (ancho %d):'
                      ' armado' % (recorrido, camara.ancho))
            ultimo_visto = recorrido
            perdido_desde = None
        elif armado:
            if perdido_desde is None:
                perdido_desde = recorrido
            elif recorrido - perdido_desde >= config.ENTRADA_PERDIDA_CM:
                print('    marcador perdido a los %.0f cm, sostenido %.1f cm'
                      % (perdido_desde, recorrido - perdido_desde))
                disparo = True
                break

        time.sleep(0.02)

    robot.frenar()
    visto = (ultimo_visto - primer_visto) if primer_visto is not None else 0.0
    if disparo:
        print('    lo vio durante %.1f cm de recorrido' % visto)
    elif not armado:
        print('    nunca vio el marcador: no hay nada que disparar.')
    return disparo, visto


def fase_buscar(robot, hub, giro, camara, boton):
    """Phase A: drive the wall, measure the gap, let the camera judge it.

    Two edges, both a jump in the lateral reading of more than
    ENTRADA_SALTO_CM: up at the mouth, back down at the far end. The
    distance between them is measured on the encoder.

    The camera runs the whole way and its sightings are remembered by
    DISTANCE, not by time: a marker seen within ENTRADA_CAMARA_RETENCION_CM
    of the gap belongs to that gap. Distance rather than seconds because
    the robot's speed is a setting and a memory measured in seconds
    would mean a different length of wall every time it changed.

    Returns (encontrada, largo_cm).
    """
    print()
    print('--- A. buscando la bahia por el lado %s ---' % config.ENTRADA_LADO)

    circ = circunferencia()
    partida = robot.traccion.position

    robot.girar(0)
    time.sleep(0.4)
    robot.avanzar(config.ENTRADA_VELOCIDAD_BUSQUEDA)

    hub.actualizar()
    referencia = lateral(hub)
    en_hueco = False
    inicio_hueco = 0.0
    largo = 0.0
    visto_en = None          # where the marker was last seen, in cm
    ancho_visto = 0
    encontrada = False

    while not boton.backspace:
        hub.actualizar()
        giro.actualizar()
        if camara is not None:
            camara.actualizar()
        d = lateral(hub)
        recorrido = vueltas_recorridas(robot, partida) * circ

        if ve_la_bahia(camara):
            visto_en = recorrido
            ancho_visto = camara.ancho

        if recorrido > config.ENTRADA_BUSQUEDA_MAXIMA_CM:
            print('    %.0f cm sin encontrar la bahia. Se para.' % recorrido)
            break

        if hub.frontal <= config.ENTRADA_FRENTE_GUARDIA_CM:
            print('    algo delante a %.0f cm. Se para la busqueda.'
                  % hub.frontal)
            break

        if not en_hueco:
            if d - referencia >= config.ENTRADA_SALTO_CM:
                en_hueco = True
                inicio_hueco = recorrido
                print('    borde cercano a los %.0f cm  (%.0f -> %.0f cm)'
                      % (recorrido, referencia, d))
            else:
                referencia = min(referencia, d)
        else:
            largo = recorrido - inicio_hueco
            # The far edge: the wall is back. Half the jump, because
            # coming back is measured against the wall distance the
            # search started from.
            if d <= referencia + config.ENTRADA_SALTO_CM / 2.0:
                print('    borde lejano  a los %.0f cm  ->  hueco de %.1f cm'
                      % (recorrido, largo))

                if largo < config.ENTRADA_LARGO_MINIMO_CM:
                    print('    descartado: %.1f cm, menos de %.1f'
                          % (largo, config.ENTRADA_LARGO_MINIMO_CM))
                elif not _confirmado(visto_en, recorrido, ancho_visto):
                    pass
                else:
                    encontrada = True
                    break

                en_hueco = False
                referencia = d
            elif largo > config.ENTRADA_LARGO_MAXIMO_CM:
                print('    el hueco pasa de %.0f cm: no es bahia, es campo'
                      ' abierto.' % config.ENTRADA_LARGO_MAXIMO_CM)
                en_hueco = False
                referencia = d

        time.sleep(0.02)

    robot.frenar()
    return encontrada, largo


def _confirmado(visto_en, recorrido, ancho):
    """Did the camera vouch for this gap? Prints why when it did not."""
    if not config.ENTRADA_CAMARA_OBLIGATORIA:
        return True
    if visto_en is None:
        print('    descartado: la camara no vio el marcador ID %d en todo'
              ' el tramo.' % config.ENTRADA_ID_BAHIA)
        return False
    atras = recorrido - visto_en
    if atras > config.ENTRADA_CAMARA_RETENCION_CM:
        print('    descartado: el marcador se vio %.0f cm atras, mas de los'
              ' %.0f de memoria.' % (atras, config.ENTRADA_CAMARA_RETENCION_CM))
        return False
    print('    CONFIRMADO por camara: marcador ID %d visto %.0f cm atras,'
          ' ancho %d' % (config.ENTRADA_ID_BAHIA, atras, ancho))
    return True


def reversa_hasta(robot, giro, boton, tope, condicion, etiqueta):
    """Reverse at a given lock until `condicion(grados)` is true.

    The gyro decides when to stop; the encoder ceiling and the stall
    detector only decide when to give up. That order matters: the target
    is an angle, and a phase that ended on distance would end wherever
    the wheelspin of the day put it.
    """
    circ = circunferencia()

    robot.girar(tope, limite=config.SALIDA_VOLANTE_TOPE)
    time.sleep(0.6)

    partida = robot.traccion.position
    robot.avanzar(-config.ENTRADA_VELOCIDAD_MANIOBRA)

    marca = time.time() + config.SALIDA_ATASCO_GRACIA
    posicion_marca = robot.traccion.position
    motivo = 'tope de recorrido'
    logrado = False

    while not boton.backspace:
        giro.actualizar()

        if condicion(giro.grados):
            motivo = 'angulo alcanzado'
            logrado = True
            break

        if (vueltas_recorridas(robot, partida) * circ
                >= config.ENTRADA_RECORRIDO_MAXIMO_CM):
            break

        ahora = time.time()
        if ahora - marca >= config.SALIDA_ATASCO_VENTANA:
            if (abs(robot.traccion.position - posicion_marca)
                    < config.SALIDA_ATASCO_GRADOS):
                motivo = 'ATASCADO: algo detras'
                break
            marca = ahora
            posicion_marca = robot.traccion.position

        time.sleep(0.01)

    robot.frenar()
    print('    %-20s %+6.1f grados, %.1f cm  (%s)'
          % (etiqueta, giro.grados,
             vueltas_recorridas(robot, partida) * circ, motivo))
    return logrado


def esta_dentro(hub, giro):
    """In the bay: parallel to the wall, and close alongside it.

    Two conditions because either alone is satisfied by a robot that is
    not in. Parallel on its own is any robot pointing down the corridor;
    close alongside on its own is any robot that ended the swing with a
    wall beside it and its nose still out.

    Returns (dentro, paralelo, pegado, lateral_cm).
    """
    hub.actualizar()
    d = lateral(hub)
    paralelo = abs(giro.grados) <= config.ENTRADA_ANGULO_TOLERANCIA
    pegado = d <= config.ENTRADA_DENTRO_LATERAL_CM
    return (paralelo and pegado), paralelo, pegado, d


def main():
    boton = Button()
    sonido = Sound()
    robot = Robot()
    giro = Giroscopio()
    hub = crear_hub()
    camara = None

    inicio = time.time()

    try:
        if config.ENTRADA_MODO not in ('completo', 'buscar', 'maniobra'):
            print('ENTRADA_MODO invalido: %r' % config.ENTRADA_MODO)
            print('Valores: completo, buscar, maniobra.')
            return

        print('=== ENTRADA AL ESTACIONAMIENTO ===')
        print('modo             : %s' % config.ENTRADA_MODO)
        print('bahia al lado    : %s' % config.ENTRADA_LADO)
        print('angulo de entrada: %.0f grados, paralelo con %.0f de margen'
              % (config.ENTRADA_ANGULO, config.ENTRADA_ANGULO_TOLERANCIA))
        print('disparo          : %s' % config.ENTRADA_DISPARO)
        print('intentos         : hasta %d, o %.0f s'
              % (config.ENTRADA_INTENTOS_MAXIMOS,
                 config.ENTRADA_TIEMPO_TOTAL_MAXIMO))
        print('guardia frontal  : para a %.0f cm en TODO avance'
              % config.ENTRADA_FRENTE_GUARDIA_CM)
        print('tope de reversa  : %.0f cm por fase, SIN sensor trasero'
              % config.ENTRADA_RECORRIDO_MAXIMO_CM)

        if config.ENTRADA_MODO in ('completo', 'buscar'):
            camara = HuskyLens()
            camara.actualizar()
            print('HuskyLens        : %s' % camara.diagnostico())
            if camara.estado in (0, 8, 9):
                print()
                print('La camara no esta lista y la busqueda la necesita.')
                if config.ENTRADA_CAMARA_OBLIGATORIA:
                    print('ENTRADA_CAMARA_OBLIGATORIA: no se arranca.')
                    return
                camara = None
            else:
                print('marcador bahia   : ID %d, ancho minimo %d px'
                      % (config.ENTRADA_ID_BAHIA,
                         config.ENTRADA_CAMARA_ANCHO_MINIMO))
        else:
            print()
            print('Modo maniobra: NO busca. Coloque el robot al lado de la')
            print('bahia, mirando a lo largo de la pared, con la bahia a la')
            print('%s. Avanza %.0f cm y entra.'
                  % (config.ENTRADA_LADO, config.ENTRADA_ARRANQUE_CM))

        print()
        print('NO hay sensor trasero. Despeje el fondo de la bahia.')
        print()

        print('Calibrando el giroscopio. No mueva el robot.')
        offset = giro.calibrar(
            mostrar=lambda h, t: print('calibrando %d/%d' % (h, t)))
        print('offset: %.2f' % offset)
        print()

        esperar_boton(boton, sonido)

        if config.ENTRADA_MODO in ('completo', 'buscar'):
            if config.ENTRADA_DISPARO == 'camara':
                listo, medida = fase_hasta_perder(robot, hub, giro,
                                                  camara, boton)
                etiqueta = 'Marcador visto durante %.1f cm.' % medida
            else:
                listo, medida = fase_buscar(robot, hub, giro, camara, boton)
                etiqueta = 'Bahia de %.1f cm.' % medida

            if not listo or boton.backspace:
                print()
                print('No se dio la senal de arranque. No se maniobra.')
                return

            print()
            print(etiqueta)
            if config.ENTRADA_MODO == 'buscar':
                print('Se para aqui: modo buscar.')
                return

            # The offset from where the trigger fired to where the
            # reverse should start. With the camera trigger this is
            # small -- the marker leaving the frame already puts the
            # robot at the edge -- and it is the number to adjust if it
            # clips the near marker or ends up short.
            if config.ENTRADA_ADELANTO_CM > 0:
                print()
                print('--- B. posicionando %.1f cm mas adelante ---'
                      % config.ENTRADA_ADELANTO_CM)
                avanzar_cm(robot, hub, boton, config.ENTRADA_ADELANTO_CM,
                           config.ENTRADA_VELOCIDAD_MANIOBRA, 'adelanto')
        else:
            print()
            print('--- B. arranque de %.1f cm (sin buscar) ---'
                  % config.ENTRADA_ARRANQUE_CM)
            robot.girar(0)
            time.sleep(0.4)
            avanzar_cm(robot, hub, boton, config.ENTRADA_ARRANQUE_CM,
                       config.ENTRADA_VELOCIDAD_MANIOBRA, 'arranque')

        if boton.backspace:
            return

        lado = signo_lado()
        limite_total = time.time() + config.ENTRADA_TIEMPO_TOTAL_MAXIMO
        dentro = False
        intento = 0

        # As many goes as it takes, bounded. One swing in is rarely
        # enough from a tight bay: it gains angle without gaining a
        # place, meets the wall, and needs another. Each go starts from
        # where the last one left the robot, so they accumulate rather
        # than repeat.
        while intento < config.ENTRADA_INTENTOS_MAXIMOS:
            if boton.backspace:
                break
            if time.time() > limite_total:
                print()
                print('%.0f s sin entrar. Se para.'
                      % config.ENTRADA_TIEMPO_TOTAL_MAXIMO)
                break

            intento += 1
            print()
            print('========== intento %d de %d =========='
                  % (intento, config.ENTRADA_INTENTOS_MAXIMOS))

            giro.reiniciar()

            print('--- C. entrando en reversa a tope ---')
            reversa_hasta(robot, giro, boton,
                          config.SALIDA_VOLANTE_TOPE * lado,
                          lambda g: abs(g) >= config.ENTRADA_ANGULO,
                          'giro de entrada')
            if boton.backspace:
                break

            print('--- D. contravolante hasta quedar paralelo ---')
            reversa_hasta(robot, giro, boton,
                          -config.SALIDA_VOLANTE_TOPE * lado,
                          lambda g: abs(g) <= config.ENTRADA_ANGULO_TOLERANCIA,
                          'vuelta a paralelo')
            if boton.backspace:
                break

            dentro, paralelo, pegado, d = esta_dentro(hub, giro)
            print('    giro %+.1f (%s), lateral %.0f cm (%s)  ->  %s'
                  % (giro.grados, 'paralelo' if paralelo else 'torcido',
                     d, 'pegado' if pegado else 'lejos',
                     'DENTRO' if dentro else 'todavia no'))

            if dentro:
                break

            if intento < config.ENTRADA_INTENTOS_MAXIMOS:
                print('--- corrección: adelante para volver a intentar ---')
                robot.girar(-config.SALIDA_VOLANTE_TOPE * lado,
                            limite=config.SALIDA_VOLANTE_TOPE)
                time.sleep(0.6)
                avanzar_cm(robot, hub, boton,
                           config.ENTRADA_CORRECCION_CM,
                           config.ENTRADA_VELOCIDAD_MANIOBRA, 'correccion')

        print()
        print('--- F. centrado ---')
        robot.girar(0)
        time.sleep(0.6)
        avanzar_cm(robot, hub, boton, config.ENTRADA_CENTRAR_CM,
                   config.ENTRADA_VELOCIDAD_MANIOBRA, 'centrado')

        hub.actualizar()
        print()
        print('%s en %d %s. frente %.0f, izq %.0f, der %.0f, giro %+.1f'
              % ('DENTRO' if dentro else 'SIN ENTRAR', intento,
                 'intento' if intento == 1 else 'intentos',
                 hub.frontal, min(hub.izquierda), min(hub.derecha),
                 giro.grados))

    finally:
        robot.apagar()
        hub.cerrar()

    print()
    print('entrada terminada en %.1f s' % (time.time() - inicio))
    sonido.beep()


if __name__ == '__main__':
    main()
