#!/usr/bin/env python3
"""Hardware diagnostics, to run before any race program.

This exists because a handful of values cannot be decided at a desk.
They depend on how this particular robot is wired and assembled, and
guessing them wrong produces failures that look like software bugs:

  1. which frame index belongs to which ultrasonic sensor;
  2. what IMU_ESCALA is, and with which sign;
  3. which way the steering turns for a positive angle;
  4. how far the steering actually travels, stop to stop;
  5. the reduction between the drive motor and the rear wheel, which is
     what makes a speed in cm/s mean anything.

Every command here either only reads, or says plainly that it moves the
robot.

Usage:
    python3 check_hw.py puertos     what ev3dev sees on each port
    python3 check_hw.py serie       raw lines from the Nano over USB
    python3 check_hw.py ultra       decoded ultrasonic frame, live
    python3 check_hw.py mapear      which index is which sensor
    python3 check_hw.py husky       raw HuskyLens values
    python3 check_hw.py imu         raw gyroscope reading
    python3 check_hw.py escala      compute IMU_ESCALA
    python3 check_hw.py lazo        full control loop, motors off
    python3 check_hw.py alimentacion power port D for the Nano
    python3 check_hw.py motores     confirm which motor is which
    python3 check_hw.py topes       measure the steering travel
    python3 check_hw.py volante     steering direction
    python3 check_hw.py reduccion   motor-to-wheel reduction, for cm/s
    python3 check_hw.py parar       stop motors and cut power
"""

import glob
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wro import config, ports


def parar():
    """Shut everything down: drive, steering and the Nano's power.

    For when something was left running because a program died without
    reaching its `finally` -- terminal closed, ssh dropped. Safe to run
    at any time.

    Worth knowing: a program killed mid-run can leave port D powering the
    Nano indefinitely, which quietly drains the battery.
    """
    for ruta in sorted(glob.glob('/sys/class/tacho-motor/motor*')):
        with open(os.path.join(ruta, 'address')) as f:
            direccion = f.read().strip()
        with open(os.path.join(ruta, 'command'), 'w') as f:
            f.write('stop')
        print('%-16s detenido' % direccion)

    for ruta in sorted(glob.glob('/sys/class/dc-motor/motor*')):
        with open(os.path.join(ruta, 'address')) as f:
            direccion = f.read().strip()
        with open(os.path.join(ruta, 'command'), 'w') as f:
            f.write('stop')
        print('%-16s sin corriente' % direccion)

    print('todo apagado')


def puertos():
    print('--- lego-port ---')
    for ruta in sorted(glob.glob('/sys/class/lego-port/port*')):
        try:
            with open(os.path.join(ruta, 'address')) as f:
                direccion = f.read().strip()
            with open(os.path.join(ruta, 'mode')) as f:
                modo = f.read().strip()
            print('%-28s %-14s %s' % (direccion, modo, os.path.basename(ruta)))
        except IOError:
            pass

    print('--- lego-sensor ---')
    for ruta in sorted(glob.glob('/sys/class/lego-sensor/sensor*')):
        with open(os.path.join(ruta, 'address')) as f:
            direccion = f.read().strip()
        with open(os.path.join(ruta, 'driver_name')) as f:
            driver = f.read().strip()
        with open(os.path.join(ruta, 'modes')) as f:
            modos = f.read().strip()
        print('%-28s %-20s %s' % (direccion, driver, modos))

    print('--- buses I2C ---')
    for ruta in sorted(glob.glob('/dev/i2c-*')):
        print(ruta)

    print('--- serie USB ---')
    encontrados = sorted(glob.glob('/dev/ttyUSB*') + glob.glob('/dev/ttyACM*'))
    if encontrados:
        for ruta in encontrados:
            print(ruta)
    else:
        print('ninguno; revise el cable del Nano y dmesg | tail')

    print('--- motores ---')
    for ruta in sorted(glob.glob('/sys/class/tacho-motor/motor*')):
        with open(os.path.join(ruta, 'address')) as f:
            direccion = f.read().strip()
        with open(os.path.join(ruta, 'driver_name')) as f:
            driver = f.read().strip()
        print('%-28s %s' % (direccion, driver))


def serie():
    """Raw lines from the Nano, exactly as they arrive over USB.

    Separates a cabling problem from a format problem. You should see
    lines like: U 34 51 125 47 30 27 91 12
    """
    import serial
    from wro.ultrasonics import HubSerial

    puerto = config.ARD_PUERTO_SERIE or HubSerial.buscar_puerto()
    print('abriendo %s a %d baudios' % (puerto, config.ARD_BAUDIOS))
    con = serial.Serial(puerto, config.ARD_BAUDIOS, timeout=1)
    time.sleep(config.ARD_ESPERA_ARRANQUE)
    con.reset_input_buffer()
    try:
        while True:
            linea = con.readline()
            if linea:
                print(linea.decode('ascii', 'replace').strip())
    except KeyboardInterrupt:
        con.close()


def husky():
    """Raw HuskyLens values through the OFDL adapter.

    Settles three things:

      - which mode to put in HUSKY_MODO;
      - what range X and Y actually arrive in, to set HUSKY_CENTRO_X/_Y
        and to check whether the axes need inverting;
      - which ID belongs to which colour, for HUSKY_ID_VERDE and
        HUSKY_ID_ROJO.

    Hold one block of each colour in front of the camera and note the ID.
    This is the only way to settle it: a swapped colour ID produces
    exactly the same symptom as reversed target signs.

    Shows the raw angle, without the hold-over filter, so a flickering
    camera is visible rather than smoothed away.
    """
    from wro.husky import HuskyLens

    cam = HuskyLens()
    print('driver   : %s' % cam.sensor.driver_name)
    print('modos    : %s' % cam.sensor.modes)
    print('modo     : %s' % cam.sensor.mode)
    print('n valores: %s' % cam.sensor.num_values)
    print()
    print('targets: VERDE %+d   ROJO %+d   (wro/config.py)'
          % (config.HUSKY_TARGET_VERDE, config.HUSKY_TARGET_ROJO))
    print()
    print('color     X  target  error  volante  lado')
    try:
        while True:
            if not cam.actualizar():
                print('%-8s  %s' % ('-', cam.diagnostico()))
            else:
                target = cam.target()
                if target is None:
                    print('%-8s ID %d no configurado como verde ni rojo'
                          % (cam.color, cam.id))
                else:
                    angulo = cam.angulo_esquive()
                    print('%-6s %+4.0f   %+4d   %+5.0f   %+6.1f  %s'
                          % (cam.color, cam.x, target, cam.x - target, angulo,
                             'DERECHA' if angulo > 0 else 'IZQUIERDA'))
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass


def ultra():
    """Show the decoded frame live.

    Cover one sensor at a time with your hand and note which column
    changes. That fills in IDX_IZQ, IDX_FRONTAL and IDX_DER in config.py.

    Both the raw and the filtered columns are shown, so it is visible
    when the filter is substituting a reading rather than reporting one.
    """
    from wro.ultrasonics import crear_hub

    hub = crear_hub()
    print('crudo                | filtrado             | valido trama  error')
    try:
        while True:
            ok = hub.actualizar()
            print('%s | %s | %s  %-6d %6.1f %s'
                  % (' '.join('%4d' % d for d in hub.distancias),
                     ' '.join('%4d' % d for d in hub.utiles),
                     format(hub.validez, '05b'), hub.trama,
                     hub.error_crudo(), '' if ok else 'CHECKSUM MALO'))
            time.sleep(0.2)
    except KeyboardInterrupt:
        print('tramas malas: %d de %d' % (hub.tramas_malas, hub.tramas_leidas))
        print('sustituciones por sensor: %s' % hub.sin_eco)
    finally:
        # Without this, a Ctrl-C leaves port D powering the Nano forever
        # and the battery drains.
        hub.cerrar()


def mapear():
    """Work out which frame index belongs to which ultrasonic sensor.

    Takes a baseline with everything clear, then asks for one sensor to
    be covered at a time. Prints the resulting IDX_ lines ready to paste
    into wro/config.py.
    """
    from wro.ultrasonics import crear_hub

    hub = crear_hub()
    try:
        _mapear(hub)
    finally:
        # Without this, quitting halfway leaves port D powering the Nano.
        hub.cerrar()


def _mapear(hub):
    CERCA = 30           # cm: below this a sensor counts as covered

    def mediana(valores):
        ordenados = sorted(valores)
        return ordenados[len(ordenados) // 2]

    def medir(segundos=2.0):
        """Median per sensor, not mean.

        These sensors emit an occasional 125 (out of range), and one
        such value shifts a mean by 20 cm. The median ignores them.
        """
        muestras = [[] for _ in range(5)]
        limite = time.time() + segundos
        while time.time() < limite:
            if hub.actualizar():
                for i in range(5):
                    muestras[i].append(hub.utiles[i])
            time.sleep(0.03)
        if not muestras[0]:
            raise IOError('no llego ninguna trama valida del Nano')
        return [mediana(m) for m in muestras]

    print('Deje los cinco ultrasonicos despejados, sin nada cerca.')
    input('Enter para tomar la linea base... ')
    base = medir()
    print('base: %s' % ' '.join('%5.0f' % v for v in base))
    print()

    posiciones = [
        ('izquierda 90', 'IZQ'),
        ('izquierda 25', 'IZQ'),
        ('frontal', 'FRONTAL'),
        ('derecha 25', 'DER'),
        ('derecha 90', 'DER'),
    ]

    hallados = []
    for nombre, grupo in posiciones:
        while True:
            input('Mano a unos 10 cm del ultrasonico %s, sostengala, Enter... '
                  % nombre)
            actual = medir()

            # A covered sensor has to satisfy TWO conditions: read close
            # in absolute terms, AND have dropped relative to its own
            # baseline. "Whichever changed most" on its own gets swamped
            # by noise, which on these sensors reaches 35 cm with nobody
            # touching them.
            usados = [h[0] for h in hallados]
            puntajes = []
            for i in range(5):
                if i in usados or actual[i] > CERCA:
                    puntajes.append(None)
                else:
                    puntajes.append(base[i] - actual[i])

            print('   tapado: %s'
                  % ' '.join('%5.0f' % v for v in actual))
            print('   bajada: %s'
                  % ' '.join('    -' if p is None else '%5.0f' % p
                             for p in puntajes))

            validos = [(p, i) for i, p in enumerate(puntajes)
                       if p is not None and p > 3]
            if validos:
                indice = max(validos)[1]
                print('   -> indice %d (sensor %d)' % (indice, indice + 1))
                print()
                hallados.append((indice, grupo))
                break

            print('   Ningun sensor libre quedo por debajo de %d cm con una'
                  % CERCA)
            print('   bajada clara. Acerque mas la mano y repita.')
            print()

    izq = [str(i) for i, g in hallados if g == 'IZQ']
    der = [str(i) for i, g in hallados if g == 'DER']
    frontal = [str(i) for i, g in hallados if g == 'FRONTAL']

    print('Pegue esto en wro/config.py:')
    print()
    print('IDX_IZQ = (%s)' % ', '.join(izq))
    print('IDX_FRONTAL = %s' % (frontal[0] if frontal else '?'))
    print('IDX_DER = (%s)' % ', '.join(der))


def imu():
    """Raw gyroscope reading, with no scaling and no offset applied."""
    from wro.imu import Giroscopio

    giro = Giroscopio(escala=1.0)
    print('Dejelo quieto: la columna cruda deberia ser casi constante.')
    try:
        while True:
            crudo = giro.lector.crudo()
            print('crudo %8d' % crudo)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


def escala():
    """Work out IMU_EJE and IMU_ESCALA in one go.

    Integrates ALL THREE gyroscope axes while the robot is turned
    through a known angle by hand. The vertical axis of this build is
    the one that accumulates a lot; the other two only pick up wobble.
    Comparing what accumulated against the real angle gives the scale,
    with its sign.

    A full turn is used rather than 90 degrees because the error of
    starting and stopping by eye then counts for four times less.

        python3 check_hw.py escala          una vuelta, 360 grados
        python3 check_hw.py escala 90       si prefieren un cuarto
    """
    import threading

    from wro.imu import Giroscopio

    objetivo = float(sys.argv[2]) if len(sys.argv) > 2 else 360.0

    giro = Giroscopio(escala=1.0)

    print('Robot quieto sobre la mesa. Calibrando el cero...')
    ceros = [0.0, 0.0, 0.0]
    MUESTRAS = 200
    for _ in range(MUESTRAS):
        lectura = giro.lector.crudo_todos()
        for i in range(3):
            ceros[i] += lectura[i] / float(MUESTRAS)
        time.sleep(0.002)
    print('cero por eje: %s' % ' '.join('%+7.2f' % c for c in ceros))
    print()

    print('Al pulsar Enter empieza a medir. Gire el robot %g grados' % objetivo)
    print('HACIA LA DERECHA, despacio y sin levantarlo, y pulse Enter otra vez.')
    input('Enter para empezar... ')

    acumulado = [0.0, 0.0, 0.0]
    picos = [0, 0, 0]
    muestras = 0
    inicio = time.time()
    ultimo = inicio

    listo = threading.Event()
    hilo = threading.Thread(target=lambda: (sys.stdin.readline(), listo.set()))
    hilo.daemon = True
    hilo.start()

    while not listo.is_set():
        lectura = giro.lector.crudo_todos()
        ahora = time.time()
        dt = ahora - ultimo
        ultimo = ahora
        for i in range(3):
            acumulado[i] += (lectura[i] - ceros[i]) * dt
            picos[i] = max(picos[i], abs(lectura[i] - ceros[i]))
        muestras += 1
        time.sleep(0.005)

    duracion = time.time() - inicio

    print()
    print('%d muestras en %.1f s  (%.0f Hz)'
          % (muestras, duracion, muestras / duracion if duracion else 0))
    print()
    print('eje   acumulado    pico crudo')
    for i in range(3):
        print(' %d   %+10.1f   %9d   %s'
              % (i, acumulado[i], picos[i], 'X Y Z'.split()[i]))
    print()

    mejor = max(range(3), key=lambda i: abs(acumulado[i]))
    segundo = sorted(range(3), key=lambda i: abs(acumulado[i]))[-2]

    if abs(acumulado[mejor]) < 1e-6:
        print('No se acumulo nada en ningun eje. El sensor no esta leyendo:')
        print('revise el cable y pruebe `python3 check_hw.py imu`.')
        return

    if abs(acumulado[mejor]) < 3 * abs(acumulado[segundo]):
        print('AVISO: el eje %d no destaca sobre el %d. Deberia acumular'
              % (mejor, segundo))
        print('mucho mas que los otros dos. Puede que haya girado poco, o')
        print('que haya inclinado el robot al girarlo. Repita mas limpio.')
        print()

    print('Pegue esto en wro/config.py:')
    print()
    print('IMU_EJE = %d' % mejor)
    print('IMU_ESCALA = %.6f' % (objetivo / acumulado[mejor]))
    print()
    print('Si la escala sale negativa, dejenla negativa: eso significa que')
    print('el sensor cuenta al reves de como esta montado, y el signo lo')
    print('corrige.')


def lazo():
    """Run the full control loop WITHOUT moving the motors.

    The dress rehearsal: reads all three sensors, computes the error,
    the steering angle and the corner count exactly as open_ard.py and
    obs_ard.py will, but sends nothing to the drive or the steering.

    Useful for two things that only show up with everything running
    together:

      - how many control loops per second actually happen, which is what
        decides whether the robot corrects in time;
      - whether the signs are consistent. Push the robot by hand towards
        a wall and check the angle comes out towards the opposite side.

    Ctrl-C to exit.
    """
    from wro.husky import HuskyLens
    from wro.imu import Giroscopio
    from wro.ultrasonics import crear_hub
    from wro.util import clamp_abs

    hub = crear_hub()
    giro = Giroscopio()

    try:
        camara = HuskyLens()
    except Exception as error:
        print('sin camara (%s); se prueba solo el seguimiento de pared'
              % error)
        camara = None

    print('Robot quieto. Calibrando el cero del giroscopio...')
    giro.calibrar(muestras=200)
    print('offset: %.2f' % giro.offset)
    print()
    print('MOTORES APAGADOS. Empuje el robot a mano.')
    print('Ctrl-C para salir.')
    print()
    print(' Hz   izq   der  error  angulo  grados esq  fuente')

    esquinas = 0
    vueltas = 0
    inicio = time.time()
    ultimo_aviso = inicio

    try:
        while True:
            arranque = time.time()

            hub.actualizar()
            angulo_imu = giro.actualizar()
            if camara is not None:
                camara.actualizar()

            if abs(angulo_imu) >= config.ANGULO_ESQUINA:
                giro.reiniciar()
                esquinas += 1

            angulo = None
            fuente = 'DIS'
            if camara is not None and camara.hay_objeto:
                angulo = camara.angulo_esquive()
                if angulo is not None:
                    fuente = 'CAM id=%d' % camara.id

            if angulo is None:
                angulo = clamp_abs(config.VOLANTE_KP * hub.error_crudo(),
                                   config.VOLANTE_LIMITE)

            vueltas += 1
            ahora = time.time()
            if ahora - ultimo_aviso >= 0.25:
                ultimo_aviso = ahora
                print('%4.0f  %4d  %4d  %+5.0f  %+6.1f  %+6.1f %3d  %s'
                      % (vueltas / (ahora - inicio),
                         sum(hub.izquierda), sum(hub.derecha),
                         hub.error_crudo(), angulo, angulo_imu,
                         esquinas, fuente))

            resto = config.PERIODO_LAZO - (time.time() - arranque)
            if resto > 0:
                time.sleep(resto)
    except KeyboardInterrupt:
        pass
    finally:
        hub.cerrar()

    duracion = time.time() - inicio
    print()
    print('%d vueltas en %.1f s = %.0f Hz'
          % (vueltas, duracion, vueltas / duracion if duracion else 0))
    print('tramas malas del Nano: %d de %d'
          % (hub.tramas_malas, hub.tramas_leidas))
    print('lecturas sin eco sustituidas, por sensor: %s' % hub.sin_eco)


def motores():
    """Confirm which motor is which, by moving one at a time.

    The movements are 15 degrees, within the usable steering travel, so
    they do not strain the stops. Even so, lift the robot or put it on a
    stand before running this.
    """
    from ev3dev2.motor import Motor

    print('--- lo que hay conectado ---')
    for ruta in sorted(glob.glob('/sys/class/tacho-motor/motor*')):
        with open(os.path.join(ruta, 'address')) as f:
            direccion = f.read().strip()
        with open(os.path.join(ruta, 'driver_name')) as f:
            driver = f.read().strip()
        print('  %-16s %s' % (direccion, driver))

    print()
    print('--- lo que dice wro/config.py ---')
    print('  PUERTO_TRACCION = %s' % config.PUERTO_TRACCION)
    print('  PUERTO_VOLANTE  = %s' % config.PUERTO_VOLANTE)
    print()
    print('Levante el robot o pongalo sobre un soporte.')

    for etiqueta, puerto in (('TRACCION', config.PUERTO_TRACCION),
                             ('VOLANTE', config.PUERTO_VOLANTE)):
        input('Enter para mover el motor de %s (%s)... ' % (etiqueta, puerto))
        motor = Motor(puerto)
        motor.stop_action = 'hold'
        inicio = motor.position
        for destino in (inicio + 15, inicio - 15, inicio):
            motor.speed_sp = 150
            motor.position_sp = destino
            motor.run_to_abs_pos()
            time.sleep(0.6)
        motor.stop(stop_action='coast')
        print('   se movio el motor de %s. Era el correcto?' % etiqueta)
        print()

    print('Si se movio el que no era, intercambie PUERTO_TRACCION y')
    print('PUERTO_VOLANTE en wro/config.py.')


def alimentacion():
    """Power port D as a current source for the Nano.

    Leaves the output at 100 %, which is continuous. Below that it would
    be a square wave, which is no use for powering electronics.
    """
    from wro.power import AlimentacionNano

    if not config.ARD_ALIMENTACION_PUERTO:
        print('ARD_ALIMENTACION_PUERTO esta en None: el Nano se alimenta')
        print('solo por USB. No hay nada que probar.')
        return

    alim = AlimentacionNano()
    print('puerto %s, ciclo de trabajo %d %%'
          % (alim.puerto, alim.duty))
    print('Mida con el multimetro entre los pines de potencia: deberia')
    print('salir la tension de la bateria, no una fraccion de ella.')
    print()
    alim.encender()
    print('encendida: %s' % alim.encendida)
    try:
        input('Enter para apagar... ')
    except (EOFError, KeyboardInterrupt):
        pass
    alim.apagar()
    print('apagada')


def topes():
    """Measure the real steering travel, stop to stop.

    Delegates to Robot.medir_topes(), the SAME routine the start-up
    auto-centring uses. There used to be two copies of this logic and one
    of them never got the power-ladder fix: `topes` measured 111 degrees
    and the auto-centring measured 11, on the same mechanism.

    Lift the robot before running this.
    """
    from wro.robot import Robot

    robot = Robot()
    input('Levante el robot y pulse Enter para buscar los topes... ')

    centro = robot.medir_topes(avisar=lambda texto: print('   %s' % texto))
    bajo, alto = robot.topes
    recorrido = robot.recorrido

    if not any(robot.movio):
        robot.volante.stop(stop_action='coast')
        print()
        print('EL VOLANTE NO SE MOVIO con ninguna potencia. Revise:')
        print('  - que PUERTO_VOLANTE (%s) sea de verdad el volante;'
              % config.PUERTO_VOLANTE)
        print('    compruebelo con: python3 check_hw.py motores')
        print('  - que la direccion no este trabada;')
        print('  - que el cable del motor este bien puesto.')
        return

    if recorrido < 10:
        robot.volante.stop(stop_action='coast')
        print()
        print('Recorrido medido: %d grados. Es demasiado poco para ser real.'
              % recorrido)
        print('Centre el volante a mano y repita.')
        return

    print('volviendo al centro...')
    robot.centro = centro
    robot.girar(0)
    time.sleep(1.0)
    robot.volante.stop(stop_action='coast')

    libre = robot.recorrido_libre
    sugerido = (libre / 2.0) * 0.85           # 15 % margin off the stops

    print()
    print('tope bajo        : %+d grados' % bajo)
    print('tope alto        : %+d grados' % alto)
    print('recorrido forzado: %d grados, empujando al 100 %%' % recorrido)
    print('recorrido libre  : %d grados, a potencia minima' % libre)
    print('centro           : %+d respecto de donde arranco' % centro)
    print()
    if recorrido - libre > 10:
        print('Los %d grados de diferencia son el mecanismo flexando contra'
              % (recorrido - libre))
        print('los topes, no direccion utilizable. La sugerencia sale del')
        print('recorrido LIBRE; con el forzado saldria %.1f, y el volante se'
              % ((recorrido / 2.0) * 0.85))
        print('pasaria la carrera peleando con los topes.')
        print()
    print('Pegue esto en wro/config.py:')
    print()
    print('VOLANTE_LIMITE = %.1f' % sugerido)


def volante():
    """Drive the steering to both logical limits to check its direction.

    Moves the steering, but not the drive train, so the robot stays put.
    """
    from wro.robot import Robot

    robot = Robot()
    robot.preparar_volante()
    for angulo in (0, config.VOLANTE_LIMITE, 0, -config.VOLANTE_LIMITE, 0):
        print('consigna %+.0f' % angulo)
        robot.girar(angulo)
        time.sleep(1.2)
    robot.apagar()
    print('Con consigna positiva el robot debe girar hacia el lado que')
    print('lo aleja de la pared izquierda. Si no, cambie VOLANTE_SIGNO.')


def reduccion():
    """Measure the reduction between the drive motor and the rear wheel.

    This is the number TRACCION_REDUCCION, and it is what turns a speed
    in cm/s into a motor command. Without it the centimetres in
    wro/config.py are an assumption of direct drive.

    The method needs no instruments: the motor's own encoder is the
    instrument. Turn a rear wheel exactly one full turn by hand and read
    how far the motor turned. If the wheel drives the motor through a
    3:1 reduction, one wheel turn is three motor turns, and the encoder
    reports 1080 degrees.

    Turn it SLOWLY. The point is the total, not the speed, and a fast
    spin can make the driver miss counts.
    """
    from ev3dev2.motor import Motor

    motor = Motor(config.PUERTO_TRACCION)
    motor.stop_action = 'coast'
    motor.stop()

    print('Motor de traccion en %s.' % config.PUERTO_TRACCION)
    print()
    print('Marque un punto de la rueda TRASERA, la negra, y pongalo abajo')
    print('tocando el piso. Levante el robot para que la rueda gire libre.')
    print()

    input('Enter cuando este listo, sin haber girado nada todavia... ')
    inicio = motor.position

    print()
    print('Ahora gire la rueda UNA vuelta completa, despacio, hasta que la')
    print('marca vuelva a quedar abajo.')
    input('Enter cuando la marca este otra vez abajo... ')

    recorrido = abs(motor.position - inicio)
    if recorrido == 0:
        print()
        print('El encoder no se movio. O la rueda no esta conectada al motor')
        print('que dice PUERTO_TRACCION, o no giro. Confirme con')
        print('`check_hw.py motores` cual motor es la traccion.')
        return

    n = recorrido / 360.0
    circunferencia_cm = math.pi * config.RUEDA_TRASERA_DIAMETRO / 10.0
    maxima = motor.max_speed / 360.0 / n * circunferencia_cm

    print()
    print('--- resultado ---')
    print('el motor giro %d grados para una vuelta de rueda' % recorrido)
    print()
    print('    TRACCION_REDUCCION = %.3f' % n)
    print()
    if n > 1.05:
        print('Va reducido %.2f a 1: el motor gira mas que la rueda, y eso' % n)
        print('cambia par por velocidad.')
    elif n < 0.95:
        print('Va multiplicado: la rueda gira mas que el motor.')
    else:
        print('Es toma directa, o casi. El 1.0 que trae el config estaba bien.')
    print()
    print('Con esta reduccion y la rueda de %.1f mm, este robot llega a'
          % config.RUEDA_TRASERA_DIAMETRO)
    print('%.1f cm/s. Ese es el techo de VELOCIDAD en cm_s.' % maxima)
    print()
    print('Repitalo dos o tres veces. Si sale distinto cada vez, gire mas')
    print('despacio: el error es de conteo, no del mecanismo.')


COMANDOS = {
    'parar': parar,
    'puertos': puertos,
    'serie': serie,
    'husky': husky,
    'ultra': ultra,
    'mapear': mapear,
    'imu': imu,
    'escala': escala,
    'lazo': lazo,
    'alimentacion': alimentacion,
    'motores': motores,
    'topes': topes,
    'volante': volante,
    'reduccion': reduccion,
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print(__doc__)
        sys.exit(1)
    COMANDOS[sys.argv[1]]()
