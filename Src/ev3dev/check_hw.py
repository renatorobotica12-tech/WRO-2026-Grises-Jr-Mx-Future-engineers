#!/usr/bin/env python3
"""Diagnostico del hardware antes de correr open_ard.py.

Resuelve en el robot las tres cosas que no se pueden decidir desde la PC:

  1. que indice de la trama corresponde a cada ultrasonico;
  2. cuanto vale IMU_ESCALA y con que signo;
  3. hacia que lado gira el volante con un angulo positivo.

Uso:
    python3 check_hw.py puertos     que ve ev3dev en cada puerto
    python3 check_hw.py serie       lineas crudas del Nano por USB
    python3 check_hw.py ultra       trama interpretada de los ultrasonicos
    python3 check_hw.py mapear      que indice es cada ultrasonico
    python3 check_hw.py husky       valores crudos de la HuskyLens
    python3 check_hw.py imu         lectura cruda del giroscopio
    python3 check_hw.py escala      calcula IMU_ESCALA
    python3 check_hw.py lazo        ensayo general, motores apagados
    python3 check_hw.py alimentacion enciende el puerto D para el Nano
    python3 check_hw.py motores     confirma cual motor es cual
    python3 check_hw.py topes       mide el recorrido de la direccion
    python3 check_hw.py volante     sentido del volante
    python3 check_hw.py parar       apaga motores y alimentacion
"""

import glob
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wro import config, ports


def parar():
    """Apaga todo: traccion, volante y la alimentacion del Nano.

    Para cuando algo quedo encendido porque un programa murio sin pasar
    por su `finally` (se cerro la terminal, se corto el ssh). Es seguro
    correrlo en cualquier momento.
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
    """Lineas crudas del Nano, tal como salen por USB.

    Sirve para separar un problema de cable de uno de formato. Deberian
    verse lineas como: U 34 51 125 47 30 27 91 12
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
    """Valores crudos de la HuskyLens por el adaptador OFDL.

    Confirma tres cosas:

      - que modo hay que poner en HUSKY_MODO (ev3dev los llama MODE0,
        MODE1... porque no conoce este sensor);
      - en que rango vienen X e Y, para ajustar HUSKY_CENTRO_X / _Y;
      - que ID le toca a cada color, para HUSKY_ID_VERDE y HUSKY_ID_ROJO.

    Pongan un bloque de cada color delante de la camara y anoten el ID.
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
    """Muestra la trama en vivo.

    Tape con la mano un sensor a la vez y anote que columna cambia. Con
    eso se llenan IDX_IZQ, IDX_FRONTAL e IDX_DER en config.py.
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
        # Sin esto, un Ctrl-C deja el puerto D alimentando al Nano para
        # siempre y se vacia la bateria.
        hub.cerrar()


def mapear():
    """Averigua que indice de la trama es cada ultrasonico.

    Toma una linea base con todo despejado y despues pide tapar uno por
    uno. El indice que mas cambie es el de ese sensor. Al final imprime
    las lineas ya listas para pegar en wro/config.py.
    """
    from wro.ultrasonics import crear_hub

    hub = crear_hub()
    try:
        _mapear(hub)
    finally:
        # Sin esto, salir a medias deja el puerto D alimentando al Nano.
        hub.cerrar()


def _mapear(hub):
    CERCA = 30           # cm: por debajo de esto se considera "tapado"

    def mediana(valores):
        ordenados = sorted(valores)
        return ordenados[len(ordenados) // 2]

    def medir(segundos=2.0):
        """Mediana de cada sensor, no promedio.

        Estos ultrasonicos sueltan lecturas de 125 (fuera de rango) de vez
        en cuando, y un solo 125 mueve el promedio 20 cm. La mediana los
        ignora.
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

            # Un sensor tapado tiene que cumplir DOS cosas: leer cerca en
            # terminos absolutos, y haber bajado respecto de su base. Solo
            # "el que mas cambio" se lo come el ruido, que en estos
            # sensores llega a 35 cm sin que nadie los toque.
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
    """Lectura cruda del giroscopio, sin escala ni offset."""
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
    """Averigua IMU_EJE e IMU_ESCALA de una sola vez.

    Integra los TRES ejes del giroscopio mientras usted gira el robot un
    angulo conocido. El eje vertical del montaje es el que acumula mucho;
    los otros dos solo recogen bamboleo. Comparando lo acumulado con el
    angulo real sale la escala, con su signo.

    Se gira una vuelta completa y no 90 grados porque el error de empezar
    y parar a ojo pesa cuatro veces menos.

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
    """Corre el lazo de control completo SIN mover los motores.

    Es el ensayo general: lee los tres sensores, calcula el error, el
    angulo de volante y las esquinas exactamente como lo hara open_ard.py
    y obs_ard.py, pero no manda nada a la traccion ni al volante.

    Sirve para dos cosas que solo se ven con todo funcionando junto:

      - cuantas vueltas de lazo por segundo salen de verdad, que es lo
        que decide si el robot corrige a tiempo;
      - si los signos cierran. Empuje el robot a mano hacia una pared y
        mire que el angulo salga hacia el lado contrario.

    Ctrl-C para salir.
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
    """Confirma cual motor es cual, moviendo uno a la vez.

    Los movimientos son de 15 grados, dentro del recorrido util de la
    direccion, asi que no fuerzan los topes. Aun asi conviene levantar el
    robot o ponerlo sobre un soporte antes de correrlo.
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
    """Enciende el puerto D como fuente de corriente para el Nano.

    Deja la salida al 100 %, que es continua. Con menos seria una onda
    cuadrada y no sirve para alimentar electronica.
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
    """Mide el recorrido real de la direccion, tope a tope.

    Delega en Robot.medir_topes(), la MISMA rutina que usa el autocentrado
    del arranque. Antes habia dos copias de esta logica y se les olvido
    copiar el escalado de potencia a una de ellas: `topes` medía 111
    grados y el autocentrado 11, con el mismo mecanismo.

    Levante el robot antes de correrlo.
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
    sugerido = (libre / 2.0) * 0.85           # 15 % de margen a los topes

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
    """Mueve el volante a los dos topes logicos para ver el sentido."""
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
}

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in COMANDOS:
        print(__doc__)
        sys.exit(1)
    COMANDOS[sys.argv[1]]()
