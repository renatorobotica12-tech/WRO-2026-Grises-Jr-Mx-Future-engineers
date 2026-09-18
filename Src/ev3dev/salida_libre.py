#!/usr/bin/env python3
"""Parking exit, free-side variant: the side is decided here, in code.

The same manoeuvre as salida.py, with one difference: which way it goes
is worked out from the lateral sensors by this file, using the three
constants below it, and the side named in config is not consulted.

salida.py is the one that obeys config. This one is for the bay whose
hand is not known until the robot is standing in it.


Starts already parked, nose towards the wall, and gets out:

    1. forward until the front sensor reads SALIDA_FRENTE_MINIMO
    2. steering over to SALIDA_LADO, reverse SALIDA_RETROCESO_CM
    3. steering to the OTHER stop, and drive out

Phases 2 and 3 are one movement in two halves, which is why the wheels
go stop to stop between them rather than through centre. Reversing with
the wheels over one way swings the tail into the bay and the nose out of
it; driving forward with them over the other way continues that same
rotation. Straightening in between would throw away half of it.

All three repeat, SALIDA_CICLOS times. One pass is rarely enough from a
tight bay: it gains angle without gaining an exit, meets the wall again,
and needs to go round once more. Each pass adds rotation to the last,
which is what a multi-point turn is.

The count is fixed rather than a condition to stop at. Every cycle runs,
and the summary at the end says how many of them finished with the way
clear.

Phase 3 does not drive a set distance and then look. It keeps going
while the nose swings round and ends the moment the front sensor reads
open space instead of wall; its distance is only a ceiling, to stop the
robot circling in a bay too open to touch a wall and too closed to read
as clear.

The front ultrasonic is the only sensor that decides anything. It ends
phase 1, and it keeps a veto in phase 3 in case another wall turns up.
The lateral pair take no part: the side to turn towards is fixed in
config rather than read from the corridor, so the manoeuvre is the same
every time and there is one line to change if the bay is mirrored.

Phase 2 is measured on the encoder: the steering goes over, the robot
backs up SALIDA_RETROCESO_CM, and it stops. There is no rear
sensor, and there IS a wall back there.

The encoder stands in for the sensor that does not exist. Wheels that
stop turning while the motor is still being told to turn them mean the
robot is pushing against something, and the reverse is cut short rather
than spent grinding into it.

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


def vueltas_recorridas(robot, partida):
    """Wheel turns since `partida`, from the drive encoder."""
    return (abs(robot.traccion.position - partida)
            / 360.0 / config.TRACCION_REDUCCION)


# ---------------------------------------------------------------
# The free-side decision, in code
# ---------------------------------------------------------------
#
# These three live here rather than in config because deciding the side
# is what this copy is for. Editing them edits this programme and
# nothing else: salida.py keeps its own behaviour whatever happens to
# these numbers.

# The tie-break. Used when neither side reads clearly further than the
# other, which is also what happens when the lateral sensors are not
# answering.
LADO_POR_DEFECTO = 'derecha'

# How much further one side has to read, in centimetres, before it is
# preferred. Below this the two are called a tie.
#
# Without a margin the choice comes down to a centimetre of ultrasonic
# noise, and a robot parked square in a symmetric bay picks its side by
# luck.
LADO_MARGEN_CM = 5.0

# Seconds of readings averaged before deciding. One frame is not a
# measurement, least of all from the lateral pair, which loses the echo
# outright when it is aimed at a wall on the slant.
LADO_MUESTREO = 0.4


# The side the whole manoeuvre turns towards. Written once, by
# elegir_lado, before the first cycle; read by everything after it.
#
# A module level value rather than an argument threaded through six
# signatures, because that is what it is: one decision, taken at the
# start, constant for the rest of the run.
_LADO = None


def lado_elegido():
    """The side the manoeuvre is turning towards.

    Falls back to LADO_POR_DEFECTO until elegir_lado has run, so
    anything asking early gets an answer rather than None.
    """
    return _LADO or LADO_POR_DEFECTO


def elegir_lado(hub):
    """Pick the exit side from the lateral sensors, once, for the run.

    More room on one side than the other is the whole test: the robot
    leaves towards the side with more of it. A tie, or a margin too
    small to trust, hands the decision back to SALIDA_LADO.

    Averaged over SALIDA_LADO_MUESTREO rather than read once. These are
    the two sensors this program otherwise keeps out of its decisions,
    precisely because they go quiet at an angle, and an average is the
    least it can take from them before betting the manoeuvre on it.
    """
    global _LADO

    # No switch to turn this off. A copy whose whole reason for existing
    # is the sensor decision does not need a way of not taking it; the
    # programme that does it the other way is salida.py, next door.
    izq = []
    der = []
    fin = time.time() + LADO_MUESTREO
    while time.time() < fin:
        hub.actualizar()
        izq.append(min(hub.izquierda))
        der.append(min(hub.derecha))
        time.sleep(0.02)

    media_izq = sum(izq) / float(len(izq)) if izq else 0.0
    media_der = sum(der) / float(len(der)) if der else 0.0
    diferencia = media_izq - media_der

    # The choice is CROSSED, and that is not a slip.
    #
    # _LADO names which way the steering goes during the REVERSE, not
    # which side the robot leaves by. The two are opposites: backing up
    # with the wheels over to the right swings the nose to the LEFT, and
    # the forward half, with the wheels at the other stop, carries on
    # that same rotation. So an exit to the left is asked for by
    # 'derecha', and the other way round.
    #
    # Read straight through, this cost a run. The free side was handed
    # in as if it named the exit, and the robot aimed itself at the one
    # wall it had just measured as the blocked side.
    if abs(diferencia) < LADO_MARGEN_CM:
        _LADO = LADO_POR_DEFECTO
        salida_por = 'izquierda' if _LADO == 'derecha' else 'derecha'
        motivo = ('empate: %.0f contra %.0f, menos de %.0f cm de diferencia'
                  % (media_izq, media_der, LADO_MARGEN_CM))
    elif diferencia > 0:
        salida_por = 'izquierda'
        _LADO = 'derecha'
        motivo = ('izquierda %.0f cm contra derecha %.0f'
                  % (media_izq, media_der))
    else:
        salida_por = 'derecha'
        _LADO = 'izquierda'
        motivo = ('derecha %.0f cm contra izquierda %.0f'
                  % (media_der, media_izq))

    print('lado libre       : %s  (%s)' % (salida_por.upper(), motivo))
    print('                   sale por la %s: retrocede con el volante a la'
          ' %s y avanza con el volante a la %s'
          % (salida_por, _LADO,
             'izquierda' if _LADO == 'derecha' else 'derecha'))
    return _LADO


def esta_fuera(hub):
    """True when the robot is out of the bay, not merely unobstructed.

    Three sensors have to agree: the front, and the nearer of each
    lateral pair. The front alone is not enough, because a robot wedged
    across a bay with a wall on either side and a gap ahead satisfies it
    and is not out of anything.

    Returns the three readings as well, so whatever refuses to clear can
    be named on the console rather than left to be guessed at.
    """
    izquierda = min(hub.izquierda)
    derecha = min(hub.derecha)
    # Two sensors, both of them: the EXIT SIDE and the FRONT.
    #
    # The robot leaves the bay towards one side, and that side's sensor
    # is the first to stop seeing wall when it is genuinely out. It is
    # what tells "in the corridor" apart from "still in the bay,
    # pointing at a gap". The front is what says there is somewhere to
    # go once it gets there: exit side open with a wall straight ahead
    # is out of the bay and into something else.
    #
    # Which sensor that is now follows elegir_lado. It used to be the
    # right one, named outright, from when the exit side was fixed in
    # config; leaving it nailed to the right would have tested the wrong
    # side of the robot on every left-hand exit.
    #
    # The other side takes no part. In a one metre corridor something is
    # always close on one side, and asking both sides to open was a
    # condition three runs never met.
    # Crossed, like the choice itself: _LADO is the steering side, so
    # the side the robot actually leaves by is the other one.
    lado_libre = izquierda if lado_elegido() == 'derecha' else derecha
    fuera = (lado_libre >= config.SALIDA_LIBRE_DERECHA
             and hub.frontal >= config.SALIDA_LIBRE)
    return fuera, hub.frontal, izquierda, derecha


def bahia_bajo_el_id(camara):
    """The camera is reporting the bay ID, whatever the detection is.

    Kept apart from ve_la_bahia so the console can tell "nothing there"
    from "something there that was thrown out", which are the two
    readings the width threshold has to be set between.
    """
    if camara is None:
        return False
    return camara.hay_objeto and camara.id == config.SALIDA_ID_BAHIA


def ve_la_bahia(camara):
    """True while the camera has the bay marker in frame.

    None when there is no camera to ask, which the caller treats as "no
    opinion" rather than as either answer.

    The ID is necessary and not sufficient. A detection also has to be
    at least SALIDA_BAHIA_ANCHO_MINIMO wide to count, because under
    changed lighting the camera reports the learned colour off walls,
    floor and reflections many times a run, and each of those false
    sightings says "still in the bay". The marker seen from inside the
    bay is large in frame; the false ones are small.

    Where in the frame it is still does not matter. The question remains
    whether the marker is visible, only now asked of something big
    enough to be it.
    """
    if camara is None:
        return None
    if not bahia_bajo_el_id(camara):
        return False
    return camara.ancho >= config.SALIDA_BAHIA_ANCHO_MINIMO


def confirmar_fuera(hub, boton, camara=None):
    """Out, held continuously for SALIDA_CONFIRMAR_SEGUNDOS.

    With a camera, the camera decides ALONE: the robot is out when the
    bay marker has left the frame. The ultrasonic test is not consulted.

    That is deliberate, not a shortcut. An ultrasonic aimed obliquely at
    a wall gets no echo, so the lateral readings go unreliable exactly
    while the robot turns out of the bay -- the part of the manoeuvre
    the test has to judge. One run showed the cost: a sensor silent on
    22 % of frames, and an exit test that three runs in a row refused to
    satisfy. A camera does not care what angle it sees a marker from.

    Without a camera the ultrasonic test is used instead, as it was
    before there was a camera in this programme.

    The window applies either way, because one frame is a coincidence.
    The marker flickers out of frame for all sorts of reasons and the
    front sensor sweeps across gaps as the robot turns; holding the
    condition for half a second is the difference between measuring
    something and glimpsing it.

    Returns (fuera, frente, izq, der, motivo).
    """
    fin = time.time() + config.SALIDA_CONFIRMAR_SEGUNDOS
    usa_camara = config.SALIDA_USAR_CAMARA and camara is not None

    while time.time() < fin and not boton.backspace:
        hub.actualizar()
        if camara is not None:
            camara.actualizar()

        # hub is read either way, so the console can report the
        # distances even when they are not what decides.
        fuera, frente, izq, der = esta_fuera(hub)

        if usa_camara:
            if ve_la_bahia(camara):
                return False, frente, izq, der, 'la bahia sigue a la vista'
        elif not fuera:
            return False, frente, izq, der, 'sensores'

        time.sleep(0.02)

    return (True, hub.frontal, min(hub.izquierda), min(hub.derecha),
            'camara' if usa_camara else 'sensores')


def fase_avanzar(robot, hub, giro, boton):
    """Phase 1: forward, steering centred, up to SALIDA_FRENTE_MINIMO.

    Two things can end this, and the second is the likely one.

    An HC-SR04 does not resolve much below 2 cm: the echo comes back
    while the transducer is still ringing from its own pulse and the
    firmware reports its out-of-range sentinel, which the filter
    eventually turns into "no wall nearby". A reading that leaps upwards
    after having been close is therefore the opposite of what it looks
    like -- the wall is nearer than ever, not further -- and it stops
    just as firmly as reaching the threshold would.
    """
    print()
    print('--- 1. avanzando hasta %.1f cm de la pared ---'
          % config.SALIDA_FRENTE_MINIMO)
    robot.girar(0)
    partida = robot.traccion.position
    limite = time.time() + config.SALIDA_TIEMPO_MAXIMO
    motivo = 'tope de recorrido'
    visto_cerca = None

    while time.time() < limite and not boton.backspace:
        hub.actualizar()
        giro.actualizar()

        # The RAW reading decides this, not the filtered one.
        #
        # hub.frontal carries a median of three frames and holds the
        # last good value for ARD_RETENCION whenever the echo fails.
        # Closing on a wall the echo starts failing BEFORE the robot
        # arrives, so the filter keeps answering with a distance already
        # passed, and a threshold below it is never crossed. The robot
        # went on advancing while the reading insisted it had not got
        # there yet.
        #
        # frontal_crudo is what the sensor measured on the last frame,
        # with no median and no hold, and None when it measured nothing.
        crudo = hub.frontal_crudo
        if crudo is not None and crudo <= config.SALIDA_FRENTE_MINIMO:
            motivo = 'distancia minima'
            break

        if hub.frontal <= config.SALIDA_FRENTE_CERCA:
            visto_cerca = (hub.frontal if visto_cerca is None
                           else min(visto_cerca, hub.frontal))
        elif (visto_cerca is not None
                and hub.frontal >= visto_cerca + config.SALIDA_FRENTE_SALTO):
            motivo = 'eco perdido a %.0f cm' % visto_cerca
            break

        if vueltas_recorridas(robot, partida) >= config.SALIDA_AVANCE_MAXIMO:
            break

        robot.avanzar(config.SALIDA_VELOCIDAD_AVANCE)
        time.sleep(0.02)
    else:
        motivo = ('boton de retroceso' if boton.backspace
                  else 'se acabo el tiempo')

    robot.frenar()
    print('    parado por %s, leyendo %.0f cm, %.2f vueltas'
          % (motivo, hub.frontal, vueltas_recorridas(robot, partida)))
    return motivo, visto_cerca


def fase_retroceder(robot, hub, giro, boton):
    """Phase 2: steering over, reverse SALIDA_RETROCESO_CM, stop.

    A distance, measured on the encoder, rather than a duration. Timed,
    this phase delivered whatever the drive train felt like giving: the
    encoder twice reported 57 % of the commanded rotation while
    reversing with the front wheels held over, so a nominal 13 cm
    arrived as about 7.4. Driving to an encoder target removes the
    question -- it stops when the wheels have turned six centimetres
    worth, whatever the friction did on the way.

    The steering goes over first and is given time to arrive. Reversing
    while the wheels are still swinging spends the movement on a curve
    that is not the one being asked for.
    """
    salida_lado = lado_elegido()
    lado = 1 if salida_lado == 'derecha' else -1
    # The manoeuvre's own stop, not the one the race drives with.
    tope = config.SALIDA_VOLANTE_TOPE * lado
    circunferencia = 3.1416 * config.RUEDA_TRASERA_DIAMETRO / 10.0

    print()
    print('--- 2. volante a la %s (%+.0f) y retroceso de %.1f cm ---'
          % (salida_lado.upper(), tope, config.SALIDA_RETROCESO_CM))

    robot.girar(tope, limite=config.SALIDA_VOLANTE_TOPE)
    time.sleep(0.6)

    giro.reiniciar()
    partida = robot.traccion.position

    robot.avanzar(-config.SALIDA_VELOCIDAD_RETROCESO)
    fin = time.time() + config.SALIDA_RETROCESO_TIEMPO_MAXIMO
    atascado = False
    motivo = 'se acabo el tiempo'

    # There is a wall behind and no sensor pointing at it. The encoder is
    # what notices: wheels that stop turning while the motor is still
    # being told to turn them mean the robot is pushing against
    # something rather than moving.
    #
    # Speed regulation sharpens this rather than blurring it. In
    # 'velocidad' mode the controller raises power to hold the commanded
    # speed, so a held wheel is a wheel being pushed harder, and a flat
    # encoder is unambiguous.
    # Not from now: the motor needs a moment to come up to speed, and
    # during it a starting wheel and a stalled one look the same. A run
    # reported "atascado: 0.34 cm de 10.0" with nothing behind the robot
    # because of exactly that.
    marca = time.time() + config.SALIDA_ATASCO_GRACIA
    posicion_marca = robot.traccion.position

    while time.time() < fin and not boton.backspace:
        giro.actualizar()

        if (vueltas_recorridas(robot, partida) * circunferencia
                >= config.SALIDA_RETROCESO_CM):
            motivo = 'distancia completada'
            break

        ahora = time.time()
        if ahora - marca >= config.SALIDA_ATASCO_VENTANA:
            avanzo = abs(robot.traccion.position - posicion_marca)
            if avanzo < config.SALIDA_ATASCO_GRADOS:
                atascado = True
                motivo = 'atascado'
                break
            marca = ahora
            posicion_marca = robot.traccion.position

        time.sleep(0.01)
    robot.frenar()

    movido = abs(robot.traccion.position - partida)
    recorrido = vueltas_recorridas(robot, partida) * circunferencia
    print('    parado por %s: %d grados = %.2f cm de %.1f, giro %+.1f'
          % (motivo, movido, recorrido, config.SALIDA_RETROCESO_CM,
             giro.grados))

    if atascado:
        print('    Las ruedas dejaron de girar con el motor mandando: hay')
        print('    algo detras. El ciclo sigue desde aqui.')
    elif motivo == 'se acabo el tiempo':
        print('    AVISO: no llego a los %.1f cm en %.0f s. O patina, o el'
              % (config.SALIDA_RETROCESO_CM,
                 config.SALIDA_RETROCESO_TIEMPO_MAXIMO))
        print('    motor no arranca a %s %%.'
              % config.SALIDA_VELOCIDAD_RETROCESO)
    return movido


def recorrer_cm(robot, boton, distancia_cm, velocidad, etiqueta):
    """Drive a signed distance on the encoder. Positive forward, back if not.

    The machinery of phase 2, pulled out so phase 4 does not have to
    reinvent a weaker copy of it. The stall detector matters most on the
    reverse, where there is no sensor and there may be a wall, but it
    costs nothing to carry on the forward moves too.

    The timeout is worked out from the speed and the distance rather
    than fixed. A flat number would be either too short for the long
    moves or useless for the short ones.

    Returns True when the distance was covered.
    """
    circunferencia = 3.1416 * config.RUEDA_TRASERA_DIAMETRO / 10.0
    partida = robot.traccion.position
    objetivo = abs(distancia_cm)
    signo = 1 if distancia_cm >= 0 else -1

    cm_s = (abs(velocidad) / 100.0
            * robot.traccion.max_speed / 360.0
            / config.TRACCION_REDUCCION
            * circunferencia)
    limite = max(2.0, config.SALIDA_RETROCESO_MARGEN_TIEMPO * objetivo / cm_s)

    robot.avanzar(signo * abs(velocidad))
    fin = time.time() + limite

    atascado = False
    motivo = 'se acabo el tiempo'
    marca = time.time() + config.SALIDA_ATASCO_GRACIA
    posicion_marca = robot.traccion.position

    while time.time() < fin and not boton.backspace:
        if vueltas_recorridas(robot, partida) * circunferencia >= objetivo:
            motivo = 'completado'
            break

        ahora = time.time()
        if ahora - marca >= config.SALIDA_ATASCO_VENTANA:
            avanzo = abs(robot.traccion.position - posicion_marca)
            if avanzo < config.SALIDA_ATASCO_GRADOS:
                atascado = True
                motivo = 'atascado'
                break
            marca = ahora
            posicion_marca = robot.traccion.position

        time.sleep(0.01)

    robot.frenar()
    recorrido = vueltas_recorridas(robot, partida) * circunferencia
    print('    %-22s %.2f cm de %.1f  (%s)'
          % (etiqueta, recorrido, objetivo, motivo))
    if atascado:
        print('        Las ruedas dejaron de girar con el motor mandando:')
        print('        hay algo ahi. El movimiento se corto.')
    return motivo == 'completado'


def fase_enderezar(robot, giro, boton):
    """Phase 4: counter-steer out of the exit arc, then give the ground back.

    Runs once, after the exit is confirmed, and only then. Four moves:

        1. SALIDA_ENDEREZAR_MARGEN_CM forward, still on the exit heading
        2. steering to the stop OPPOSITE the exit, then
           SALIDA_ENDEREZAR_AVANCE_CM forward on that lock
        3. steering centred
        4. SALIDA_ENDEREZAR_RETROCESO_CM back

    The opposite stop is computed the same way phase 3 computes its own
    and then negated, so the two stay mirrored however the side was
    chosen. Leaving to the right means phase 3 steered right, and this
    phase steers left.

    The back button ends it between moves as well as during them, and a
    move that is cut short does not stop the ones after it: a phase that
    abandons the robot mid-counter-steer would leave it worse placed
    than not running at all.
    """
    lado = 1 if lado_elegido() == 'derecha' else -1
    tope_salida = -config.SALIDA_VOLANTE_TOPE * lado
    tope = -tope_salida

    print()
    print('--- 4. enderezado: contravolante a %+.0f ---' % tope)
    giro.reiniciar()

    # Two run-ups, and they are different movements. The first keeps the
    # exit lock and goes on turning; the second centres and goes
    # straight. Either can be set to 0 and skipped without the other
    # noticing.
    if config.SALIDA_ENDEREZAR_ARCO_CM > 0:
        recorrer_cm(robot, boton, config.SALIDA_ENDEREZAR_ARCO_CM,
                    config.SALIDA_ENDEREZAR_VELOCIDAD,
                    'arco, volante de salida')

    if config.SALIDA_ENDEREZAR_MARGEN_CM > 0 and not boton.backspace:
        robot.girar(0)
        time.sleep(0.6)
        recorrer_cm(robot, boton, config.SALIDA_ENDEREZAR_MARGEN_CM,
                    config.SALIDA_ENDEREZAR_VELOCIDAD, 'margen recto')

    if not boton.backspace:
        robot.girar(tope, limite=config.SALIDA_VOLANTE_TOPE)
        time.sleep(0.6)
        recorrer_cm(robot, boton, config.SALIDA_ENDEREZAR_AVANCE_CM,
                    config.SALIDA_ENDEREZAR_VELOCIDAD, 'sobre el contravolante')

    if not boton.backspace:
        robot.girar(0)
        time.sleep(0.6)
        recorrer_cm(robot, boton, -config.SALIDA_ENDEREZAR_RETROCESO_CM,
                    config.SALIDA_ENDEREZAR_VELOCIDAD, 'atras, centrado')

    robot.girar(0)
    print('    giro acumulado en la fase: %+.1f grados' % giro.grados)


def fase_salir(robot, hub, giro, boton):
    """Phase 3: steering to the OTHER stop, and drive out.

    Not back to centre. The wheels go from one stop straight to the
    other, and that is what makes the manoeuvre work: reversing with the
    wheels over one way swings the tail into the bay and the nose out of
    it, and driving forward with them over the other way continues the
    same rotation instead of undoing it. Centring here would drive the
    robot out along whatever heading the reverse happened to leave it
    on.

    The front sensor still has a veto: another wall appearing ahead
    means the bay was not where the robot thought it was, and completing
    the exit would be driving into something.
    """
    lado = 1 if lado_elegido() == 'derecha' else -1
    # The opposite stop to the one the reverse used. Both read the same
    # chosen side, so they stay mirrored whichever way it went.
    tope = -config.SALIDA_VOLANTE_TOPE * lado

    print()
    print('--- 3. volante al otro tope (%+.0f) y adelante ---' % tope)

    robot.girar(tope, limite=config.SALIDA_VOLANTE_TOPE)
    time.sleep(0.6)

    giro.reiniciar()
    partida = robot.traccion.position
    limite = time.time() + config.SALIDA_TIEMPO_MAXIMO
    motivo = 'recorrido completado'
    rapido = False

    while time.time() < limite and not boton.backspace:
        hub.actualizar()
        giro.actualizar()

        # Keep going until the front opens up. This is the ending the
        # phase is for: the nose swings out as the robot turns, and the
        # moment the sensor sees room instead of wall, it is out.
        #
        # But not before moving. The phase begins right after an approach
        # that ended on a lost echo, nose against the wall, and a lost
        # echo is exactly what the filter turns into "no wall nearby"
        # once ARD_RETENCION expires. So the first reading here can say
        # 100 cm with the robot touching the wall.
        #
        # On track it did, every time: five cycles that each reported
        # "parado por libre: 0.00 vueltas". The phase declared success
        # before turning a wheel, the robot never drove out, and the
        # manoeuvre was approach, reverse, nothing, repeat.
        #
        # Requiring SALIDA_SALIR_MINIMO first costs a few centimetres and
        # makes the reading real: by then the sensor has had echoes back
        # from wherever the robot now is.
        if (vueltas_recorridas(robot, partida) >= config.SALIDA_SALIR_MINIMO
                and hub.frontal >= config.SALIDA_LIBRE):
            motivo = 'libre'
            break
        if hub.frontal <= config.SALIDA_FRENTE_MINIMO:
            motivo = 'otra pared al frente'
            break
        # Distance is a ceiling, not a target. Driving forward at full
        # lock is driving in a circle, and without this the robot would
        # keep circling in a bay too open to touch a wall and too closed
        # to read as clear.
        if vueltas_recorridas(robot, partida) >= config.SALIDA_SALIR_VUELTAS:
            motivo = 'tope de recorrido'
            break

        # Two stages. The phase starts a few centimetres from the wall
        # the robot has just been nosing into and ends out in the
        # corridor, and one speed cannot suit both ends of that: slow
        # enough for the start is slow enough to stretch the rest, four
        # times over across four cycles.
        #
        # Read off the filtered value on purpose. Speeding up is the
        # decision that can afford to wait a frame, and it should not be
        # taken on one reading that happened to come back long.
        if hub.frontal >= config.SALIDA_SALIR_LIBRE_CM:
            if not rapido:
                rapido = True
                print('    %.0f cm al frente: acelerando a %s'
                      % (hub.frontal, config.SALIDA_VELOCIDAD_SALIDA_RAPIDA))
            robot.avanzar(config.SALIDA_VELOCIDAD_SALIDA_RAPIDA)
        else:
            rapido = False
            robot.avanzar(config.SALIDA_VELOCIDAD_SALIDA)

        time.sleep(0.02)
    else:
        # The loop condition covers two different endings and they must
        # not be reported as one. On the first run this printed "se
        # acabo el tiempo" after six seconds of a 185 second phase,
        # because the back button had been pressed, and the console said
        # the opposite of what had happened.
        motivo = ('boton de retroceso' if boton.backspace
                  else 'se acabo el tiempo')

    robot.frenar()
    print('    parado por %s: %.2f vueltas, giro %+.1f grados'
          % (motivo, vueltas_recorridas(robot, partida), giro.grados))
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
    print('avance           : %s' % robot.describir_velocidad(
        config.SALIDA_VELOCIDAD_AVANCE))
    print('retroceso        : %s' % robot.describir_velocidad(
        config.SALIDA_VELOCIDAD_RETROCESO))
    print('salida           : %s' % robot.describir_velocidad(
        config.SALIDA_VELOCIDAD_SALIDA))
    print('frente minimo    : %.1f cm' % config.SALIDA_FRENTE_MINIMO)
    _cm_s = (abs(config.SALIDA_VELOCIDAD_RETROCESO) / 100.0
             * robot.traccion.max_speed / 360.0
             / config.TRACCION_REDUCCION
             * 3.1416 * config.RUEDA_TRASERA_DIAMETRO / 10.0)
    print('retroceso        : %.1f cm al lado que elijan los sensores,'
          ' %.0f grados de encoder'
          % (config.SALIDA_RETROCESO_CM,
             config.SALIDA_RETROCESO_CM
             / (3.1416 * config.RUEDA_TRASERA_DIAMETRO / 10.0) * 360
             * config.TRACCION_REDUCCION))
    print('                   deberia tardar %.1f s, corta a los %.0f'
          % (config.SALIDA_RETROCESO_CM / _cm_s,
             config.SALIDA_RETROCESO_TIEMPO_MAXIMO))
    print('TOPES            : izquierda %+.1f  centro 0  derecha %+.1f'
          % (config.VOLANTE_TOPE_IZQUIERDO, config.VOLANTE_TOPE_DERECHO))
    print()
    print('El sensor no resuelve bajo ~2 cm: lo normal es que la fase 1')
    print('pare por eco perdido y no por distancia. No es un fallo.')
    print('NO hay sensor trasero. Despeje lo que haya detras del robot.')
    print()

    esperar_boton(boton, sonido)

    hub.actualizar()
    inicio = time.time()

    fuera = False
    ciclos = 0
    mejor_frente = mejor_izq = mejor_der = 0.0

    # Opened now, before the manoeuvre, because the same camera serves
    # the race afterwards: opening it twice would reset the adapter in
    # the middle of a run.
    #
    # A camera that is not ready is not a reason to refuse the
    # manoeuvre. The ultrasonic test stands on its own, and did, before
    # there was a camera in this programme at all. It only means this
    # run decides by sensors.
    camara = None
    if config.SALIDA_USAR_CAMARA:
        camara = HuskyLens()
        camara.actualizar()
        print('HuskyLens: %s' % camara.diagnostico())
        if camara.estado in (0, 8, 9):
            print('La camara no esta lista: se sale solo por sensores.')
            print('Para usarla, el marcador de la bahia tiene que estar')
            print('aprendido con el ID %d.' % config.SALIDA_ID_BAHIA)
            camara = None
        else:
            print('marcador de bahia: ID %d. Mientras se vea, sigue ciclando.'
                  % config.SALIDA_ID_BAHIA)
        print()

    # Before the first cycle, and only here. Every phase reads the result
    # rather than deciding for itself, which is what keeps all the passes
    # turning the same way.
    elegir_lado(hub)
    print()

    try:
        # The cycle repeats, approach included, until the robot is out or
        # the passes run out. Each one is forward to the wall, back with
        # the wheels one way, forward with them the other, and each adds
        # rotation to the last. That is a multi-point turn.
        #
        # It stops the moment the robot is out rather than finishing the
        # five: a cycle begun from outside the bay would drive the robot
        # back towards whatever it just escaped.
        # With the camera deciding, the cycles are not counted: the robot
        # keeps working at the bay for as long as the marker is in
        # frame. There is nothing arbitrary left to stop it at, and
        # stopping at an arbitrary number was what left the robot half
        # out on earlier runs.
        #
        # It is bounded all the same, by three things that are not
        # arbitrary: the back button, the stall detector when the wheels
        # meet the wall behind, and SALIDA_TIEMPO_TOTAL_MAXIMO as the
        # backstop for a robot that is getting nowhere.
        #
        # A cycle is also not a net movement backwards -- forward to the
        # wall, back 4 cm, forward again on the arc -- so repeating it
        # does not walk the robot into the wall behind however many
        # times it runs.
        sin_tope = config.SALIDA_USAR_CAMARA and camara is not None
        limite_total = time.time() + config.SALIDA_TIEMPO_TOTAL_MAXIMO
        numero = 0

        while True:
            if boton.backspace:
                break
            if not sin_tope and numero >= config.SALIDA_CICLOS:
                break
            if time.time() > limite_total:
                print()
                print('%.0f s en la bahia sin salir. Se para.'
                      % config.SALIDA_TIEMPO_TOTAL_MAXIMO)
                break

            numero += 1
            ciclos = numero
            print()
            print('========== ciclo %d %s =========='
                  % (numero, '(sin tope, manda la camara)' if sin_tope
                     else 'de %d' % config.SALIDA_CICLOS))

            fase_avanzar(robot, hub, giro, boton)
            if boton.backspace:
                break

            fase_retroceder(robot, hub, giro, boton)
            if boton.backspace:
                break

            fase_salir(robot, hub, giro, boton)
            if boton.backspace:
                break

            fuera, frente, izq, der, via = confirmar_fuera(hub, boton, camara)
            # Report the width either way. Accepted and discarded are
            # the two ranges SALIDA_BAHIA_ANCHO_MINIMO has to sit
            # between, and without printing both there is nothing to set
            # it from but guesswork.
            if camara is None:
                estado_bahia = '-'
            elif ve_la_bahia(camara):
                estado_bahia = 'a la vista (ancho %d)' % camara.ancho
            elif bahia_bajo_el_id(camara):
                estado_bahia = ('DESCARTADA por chica (ancho %d < %d)'
                                % (camara.ancho,
                                   config.SALIDA_BAHIA_ANCHO_MINIMO))
            else:
                estado_bahia = 'no'

            print('    frente %.0f, izquierda %.0f, derecha %.0f, bahia %s'
                  '  ->  %s'
                  % (frente, izq, der, estado_bahia,
                     ('FUERA por ' + via) if fuera else 'todavia no'))

            # The best each sensor managed across the whole run. Without
            # this the numbers that explain a failure are five separate
            # lines of scrollback, and by the time anybody looks the
            # robot has been picked up and the readings are gone.
            mejor_frente = max(mejor_frente, frente)
            mejor_izq = max(mejor_izq, izq)
            mejor_der = max(mejor_der, der)

            if fuera:
                break

        # Once, and only after the exit is confirmed.
        if fuera and config.SALIDA_ENDEREZAR and not boton.backspace:
            fase_enderezar(robot, giro, boton)

        if not fuera:
            print()
            print('No quedo fuera en %d %s.'
                  % (ciclos, 'ciclo' if ciclos == 1 else 'ciclos'))
            print()
            print('               lo mejor    hace falta')
            print('   derecha     %6.0f      %6d %s'
                  % (mejor_der, config.SALIDA_LIBRE_DERECHA,
                     '' if mejor_der >= config.SALIDA_LIBRE_DERECHA
                     else '  <-- corto'))
            print('   frente      %6.0f      %6d %s'
                  % (mejor_frente, config.SALIDA_LIBRE,
                     '' if mejor_frente >= config.SALIDA_LIBRE
                     else '  <-- corto'))
            print('   (izquierda %.0f: no decide nada, va solo de referencia)'
                  % mejor_izq)
            print()
            print('Hacen falta las DOS. Si en pista se veia fuera, baje la que')
            print('sale corta a un poco menos que su mejor lectura.')

        elif config.SALIDA_SEGUIR_CON_OBSTACULOS and not boton.backspace:
            print()
            print('=' * 50)
            print('  FUERA del estacionamiento: OBSTACLE CHALLENGE')
            print('=' * 50)

            import obs_ard
            # Reuse the one opened for the manoeuvre. Constructing a
            # second HuskyLens resets the adapter, and doing that between
            # leaving the bay and the first lap would cost the race its
            # opening seconds of vision.
            if camara is None:
                camara = HuskyLens()
            camara.actualizar()
            print('HuskyLens: %s' % camara.diagnostico())
            if camara.estado in (0, 8, 9):
                print('La camara no esta lista. No se arranca la carrera.')
            else:
                # Straight through. There is ONE button in this program
                # and it is the one at the start of the run; nothing
                # pauses between coming out of the bay and the first lap,
                # because the competition sequence does not pause there.
                #
                # This is safe because being out was confirmed over a
                # window rather than read once, and because the two
                # calibrations the chain skips are already done and still
                # valid. Nothing reaching this line is unverified.
                obs_ard.correr(robot, hub, giro, camara, boton, sonido)
                return

        print('Desde aqui sigue la programacion normal.')
    finally:
        robot.apagar()
        hub.cerrar()

    print()
    print('maniobra terminada en %.1f s, %d %s, %s'
          % (time.time() - inicio, ciclos,
             'ciclo' if ciclos == 1 else 'ciclos',
             'FUERA' if fuera else 'sin salir'))
    print('tramas malas del Nano: %d de %d, lecturas fallidas: %d'
          % (hub.tramas_malas, hub.tramas_leidas, hub.lecturas_fallidas))
    sonido.beep()


if __name__ == '__main__':
    main()
