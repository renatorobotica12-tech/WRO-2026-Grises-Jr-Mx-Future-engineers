"""Configuracion del robot: puertos, cableado y ganancias.

Todo lo que hay que tocar en pista deberia estar en este archivo.
Los valores vienen del programa EV3 `OPEN_ARD` y de los programas Arduino
`WRO OPEN ARD-UNO.mp` y `WRO OBS ARD-UNO.mp` de Arath.
"""

# --------------------------------------------------------------------
# Puertos
# --------------------------------------------------------------------

PUERTO_IMU = 'ev3-ports:in2'        # mindsensors AbsoluteIMU
PUERTO_HUSKY = 'ev3-ports:in3'      # HuskyLens por el adaptador OFDL
PUERTO_ARD = 'ev3-ports:in4'        # solo si el Nano va por I2C

# Confirmado en el robot: los DOS motores son medianos (lego-ev3-m-motor),
# y no hay nada en C ni en D. No coincide con OPEN_ARD_EQUIVALENCIA.md,
# que hablaba de un motor grande en D.
PUERTO_TRACCION = 'outB'            # motor mediano
PUERTO_VOLANTE = 'outA'             # motor mediano

# --------------------------------------------------------------------
# Arduino Nano multiplexor de ultrasonicos
# --------------------------------------------------------------------

# 'serial' -> firmware ultrasonic_hub_serial, Nano al puerto USB del ladrillo
# 'i2c'    -> firmware ultrasonic_hub_packet, Nano a un puerto de sensores
ARD_BACKEND = 'serial'

ARD_PUERTO_SERIE = None             # None = autodetectar /dev/ttyUSB* o ttyACM*
ARD_BAUDIOS = 115200
ARD_ESPERA_ARRANQUE = 2.0           # el Nano se reinicia al abrir el puerto

# Alimentacion del Nano desde un puerto de motores, tratandolo como motor
# de corriente continua. Los datos siguen yendo por USB.
# Pongan None si el Nano se alimenta solo por USB.
#
# El ciclo de trabajo DEBE ser 100: por debajo la salida del EV3 es una
# onda cuadrada, no continua, y el regulador del Nano lo pasaria mal.
ARD_ALIMENTACION_PUERTO = 'outD'
ARD_ALIMENTACION_DUTY = 100
ARD_ALIMENTACION_ESPERA = 1.5       # segundos antes de abrir el puerto serie

ARD_DIRECCION = 0x08                # solo para ARD_BACKEND = 'i2c'
ARD_FIRMWARE = 'packet'             # 'packet' o 'byte'

# Indices base cero dentro de la trama.
# Verificado en el robot con `check_hw.py mapear`, tapando un sensor a la
# vez. Coincide con lo que decia documentos/OPEN_ARD_EQUIVALENCIA.md.
IDX_IZQ = (0, 1)                    # 90izq y 25izq
IDX_FRONTAL = 2
IDX_DER = (3, 4)                    # 25der y 90der

ARD_FUERA_DE_RANGO = 125            # valor de sustitucion del firmware

# --------------------------------------------------------------------
# Filtrado de las distancias
# --------------------------------------------------------------------
#
# Esto NO esta en el programa de Arath: es un anadido deliberado.
#
# Cuando un ultrasonico no recibe eco, el firmware devuelve 125 y baja su
# bit de validez. 125 no es una distancia, es un centinela. Sumandolo tal
# cual al error, un solo parpadeo de un sensor hace que el error salte
# 80 cm y el volante pegue un volantazo al tope. Medido con
# `check_hw.py lazo`: el error salto de +5 a -82 y volvio a +31 en menos
# de un segundo, con el robot inmovil.
#
# Con el filtro, un sensor que se queda sin eco conserva su ultima
# lectura buena durante ARD_RETENCION segundos; si sigue sin eco despues
# de eso, se da por "no hay pared cerca" y se usa ARD_DISTANCIA_MAXIMA.
ARD_FILTRAR = True

# Tope util de distancia, en cm. Mas alla de esto la lectura no aporta
# nada para centrarse entre paredes y solo mete ruido en el error.
# El pasillo de Future Engineers es de 1 m; los sensores a 25 grados ven
# algo mas que la perpendicular, de ahi el margen.
ARD_DISTANCIA_MAXIMA = 100

# Cuanto se conserva la ultima lectura buena de un sensor sin eco.
# A 44 Hz son unas 22 vueltas de lazo.
ARD_RETENCION = 0.5

# Mediana movil por sensor, para matar picos sueltos que pasan la
# validez. 1 la desactiva; 3 es suficiente y no agrega retraso notable.
ARD_MEDIANA = 3

# --------------------------------------------------------------------
# IMU
# --------------------------------------------------------------------

# 'driver' -> sensor lego-sensor con driver ms-absolute-imu (recomendado)
# 'raw'    -> lectura I2C directa de los registros del giroscopio
IMU_BACKEND = 'driver'

IMU_DIRECCION = 0x11                # 0x22 de 8 bits = 0x11 de 7 bits
IMU_DRIVER = 'ms-absolute-imu'
IMU_MODO = 'GYRO'
IMU_EJE = 2                         # 0=X, 1=Y, 2=Z

# Factor para pasar de la lectura cruda a grados por segundo.
#
# El driver ms-absolute-imu en modo GYRO reporta units = d/s y
# decimals = 1: el entero crudo viene multiplicado por diez. De ahi sale
# 0.1 exacto. No es el 0.001 del bloque de EV3-G, que si entrega
# mili-grados/s.
#
# Confirmado midiendo: `check_hw.py escala` con una vuelta completa dio
# 0.09795, que coincide al 2 %. Se deja 0.1 y no la medicion, porque 0.1
# es exacto por construccion y la medicion lleva dentro el error de girar
# el robot a mano. La prueba sirvio para confirmar el eje y el signo.
#
# Signo POSITIVO confirmado: girando a la derecha, Z acumula positivo.
IMU_ESCALA = 0.1

IMU_MUESTRAS_CALIBRACION = 600      # igual que mpu.calibrar(600) de Arath
IMU_ZONA_MUERTA = 0.3               # grados/s; equivalente de zonaMuerta(0.3)

# --------------------------------------------------------------------
# HuskyLens
# --------------------------------------------------------------------

# Confirmado en el robot: ev3dev detecta el adaptador como `ev3-uart-84`
# y sus modos si traen nombre propio, no MODE0/MODE1.
#   'Data-EV3HSK' -> los datos del recuadro
#   'Time-EV3HSK' -> otro modo del adaptador, sin usar aqui
HUSKY_MODO = 'Data-EV3HSK'

# Orden real de los ocho valores, medido en el robot. NO es el que dice
# el README del adaptador (State, ID, X, Y, W, H): el State esta en el
# indice 5, y cuando no hay deteccion los demas se van a cero.
# Los indices 6 y 7 siempre salen 0 en este modo.
HUSKY_IDX_X = 0
HUSKY_IDX_Y = 1
HUSKY_IDX_W = 2
HUSKY_IDX_H = 3
HUSKY_IDX_ID = 4
HUSKY_IDX_STATE = 5

# Resolucion de la HuskyLens. Se resta para dejar el origen en el centro
# de la imagen, como el map(x, 0,320, -160,160) de Arath.
HUSKY_CENTRO_X = 160
HUSKY_CENTRO_Y = 120

# Inversion de ejes, para cuando el lente entrega la imagen al reves.
#
# Con el lente de 125 grados la imagen llega girada respecto del lente
# original. Se corrige aqui y no en los targets a proposito: invirtiendo
# el eje, todo lo que viene despues (targets, recortes, signo del volante)
# sigue significando lo mismo que siempre y no hay que retocar nada mas.
#
# X es el unico que afecta al comportamiento: es el que usa
# angulo_esquive(). Con X invertida al reves de como esta montado el
# lente, el robot esquiva cada bloque por el lado contrario.
#
# Y no interviene en ninguna decision hoy; se invierte por coherencia,
# para que el par (X, Y) describa la imagen de verdad.
#
# Verificado con `check_hw.py husky`: con el bloque a la IZQUIERDA de la
# camara, X tiene que salir NEGATIVA.
#
# Con el lente de 125 grados hubo que poner los dos en True, y se
# comprobo midiendo: izquierda -140, centro -2, derecha +81. Con el lente
# original la imagen no viene girada, asi que vuelven a False. SI SE
# CAMBIA DE LENTE OTRA VEZ, hay que volver a medirlo: es lo primero que
# se rompe y no da error, solo hace que el robot esquive al reves.
HUSKY_INVERTIR_X = False
HUSKY_INVERTIR_Y = False

# IDs aprendidos en la HuskyLens, en modo reconocimiento de color.
#
# Medidos poniendo cada bloque delante y leyendo el ID, no deducidos:
# el rojo es el 1 y el verde es el 2. Estuvieron cruzados un tiempo, y el
# robot funcionaba igual porque los targets tambien estaban cruzados; lo
# que fallaba era que al ajustar HUSKY_TARGET_ROJO se estaba tocando el
# verde. Si alguna vez se reaprenden los colores en la camara, hay que
# volver a medirlo con `check_hw.py husky`.
HUSKY_ID_ROJO = 1
HUSKY_ID_VERDE = 2

# ESTE ES EL MANDO PARA AJUSTAR EL ESQUIVE DE LOS PILARES.
#
# Es la posicion, en pixeles, donde el robot intenta DEJAR el bloque
# dentro de la imagen mientras lo rodea. El volante corrige hasta que el
# bloque llega ahi:
#
#   -160  borde izquierdo de la imagen
#      0  centro
#   +160  borde derecho
#
# Si el bloque tiene que acabar a la IZQUIERDA de la imagen, es que el
# robot esta apuntando a la derecha de el, o sea que lo pasa por la
# DERECHA. Suena al reves la primera vez: es porque la camara mira hacia
# donde va el robot, no hacia el bloque.
#
#   target mas lejos del centro  ->  rodeo mas amplio, se aleja mas
#   target mas cerca del centro  ->  lo esquiva mas justo
#   target 0                     ->  apunta al bloque y se lo lleva por
#                                    delante
#
# Van por color para poder abrir mas el rodeo de uno que el del otro.
#
# Que color lleva que signo se fijo probando en pista, no deduciendolo:
# la primera version razonada los pasaba por el lado contrario.
#
# OJO: un ID de color intercambiado da exactamente el mismo sintoma que
# los signos al reves, y se "arregla" igual. `check_hw.py husky` con un
# bloque de cada color delante dice que ID le toca a cada uno de verdad.
# El techo real es +-160: X se calcula como raw - HUSKY_CENTRO_X sobre una
# imagen de 320 px, asi que el bloque no puede estar mas alla. Un target
# fuera de ese rango es una posicion inalcanzable, y el volante nunca
# llegaria a centrarse mientras viera el bloque: se quedaria girando hasta
# que el pilar se saliera del cuadro. Con 150 el lazo todavia cierra.
#
# Subidos de 140 a 150 para abrir el rodeo con el lente de 125 grados,
# que al repartir la misma resolucion sobre mas campo deja los bloques
# mas pequenos y mas cerca del centro.
HUSKY_TARGET_ROJO = -150            # a la izquierda -> lo pasa por la derecha
HUSKY_TARGET_VERDE = +150           # a la derecha  -> lo pasa por la izquierda

# Recorte del angulo de volante para cada color, como FRACCION del tope.
#
# Arath recorta con constrain(..., 75, 110) y constrain(..., 70, 110)
# sobre un servo centrado en 90 cuyo tope es +-20. En fracciones del tope
# eso es -0.75..+1.0 y -1.0..+1.0: el recorte apretado va con el color
# que gira a la derecha, y aqui se mantiene esa correspondencia.
#
# Van en fracciones y no en grados a proposito: en grados quedarian
# atados al +-20 de aquel servo y recortarian a un tercio del recorrido
# real de esta direccion.
HUSKY_LIMITE_ROJO = (-0.75, 1.0)    # el que da consigna positiva
HUSKY_LIMITE_VERDE = (-1.0, 1.0)

# Cuanto se sostiene la ultima orden buena de la camara, en segundos.
#
# Mismo patron que ARD_RETENCION para los ultrasonicos, y por la misma
# razon: un fallo de una trama no es "el bloque ya no esta".
#
# Resuelve DOS problemas medidos en pista:
#
#   1. Parpadeos. La camara pierde el bloque una o dos vueltas y el mando
#      volvia al seguimiento de pared, que en ese instante veia un error
#      grande y mandaba el volante al tope. Medido: de +1.9 a +50.6 y de
#      vuelta en 300 ms, con el bloque delante todo el tiempo.
#
#   2. Alternancia entre bloques. Con dos bloques a la vista, el adaptador
#      OFDL no entrega siempre el mismo recuadro: va saltando de uno a
#      otro entre lecturas. Medido: id=1 pidiendo +50.6 (derecha) y 300 ms
#      despues id=2 pidiendo -27.2 (izquierda). Mientras el bloque
#      enganchado se siga viendo dentro de esta ventana, los demas se
#      ignoran.
#
# El tamano sale del periodo real del lazo, no a ojo: a los 31 Hz medidos
# cada vuelta son 32 ms, asi que por debajo de eso la ventana expira antes
# de la siguiente lectura y la retencion no llega a activarse nunca. Con
# 0.1 s cubre 3 vueltas, que es lo que duraron los parpadeos observados.
#
# Subirlo ayuda si el robot sigue bailando entre dos bloques; bajarlo lo
# hace mas reactivo. Pasarse es malo: el robot seguiria girando hacia un
# bloque que ya dejo atras.
#
# El recorrido de este numero esta medido, no supuesto:
#
#   0.1  ->  12 % de vueltas retenidas. Cubria los parpadeos.
#   0.3  ->  31 % de vueltas retenidas, y el alternado SEGUIA igual.
#
# Lo segundo enseño algo: el adaptador no alterna trama a trama, cambia de
# bloque durante periodos mas largos que la ventana. Alargarla no lo
# alcanza nunca, solo hace que el robot actue sobre imagenes viejas: a
# velocidad 40, un tercio de las ordenes con hasta 0.3 s de retraso.
#
# Asi que la ventana vuelve a lo que sabe hacer bien, tapar parpadeos, y
# del alternado se encarga HUSKY_MARGEN_ANCHO, que es el criterio
# correcto para eso.
HUSKY_RETENCION = 0.15

# Cuanto mas ancho tiene que verse un bloque nuevo para quitarle el mando
# al que ya se estaba esquivando. 1.0 acepta cualquiera; 1.2 exige que se
# vea un 20 % mas ancho.
#
# El ancho del recuadro es el unico dato de PROXIMIDAD que da el
# adaptador: los pilares de la pista son todos iguales, asi que el que se
# ve mas ancho es el que esta mas cerca, y el mas cercano es el que hay
# que esquivar. Sin este criterio, con dos bloques a la vista el robot
# recibia ordenes de lados opuestos en vueltas consecutivas: medido,
# id=1 pidiendo +50.6 (derecha) y 300 ms despues id=2 pidiendo -27.2.
#
# Es lo que Arath consigue pidiendo los dos primeros recuadros y quedandose
# con el mas ancho. Este adaptador entrega uno solo por lectura, pero
# comparando entre lecturas se recupera el mismo criterio.
#
# El 20 % de margen es histeresis: sin el, dos bloques a distancia
# parecida se turnarian el mando por el ruido de la medicion.
HUSKY_MARGEN_ANCHO = 1.2

# --------------------------------------------------------------------
# Volante
# --------------------------------------------------------------------

# Grados del motor que equivalen al tope de direccion.
#
# Medido con `check_hw.py topes` en este robot:
#
#   tope bajo -88, tope alto +65, centro -12
#   recorrido forzado 153 grados (empujando al 100 %)
#   recorrido libre   119 grados (a potencia minima)
#
# Los 34 de diferencia son el mecanismo flexando contra los topes, no
# direccion utilizable: el limite sale del recorrido LIBRE, con un 15 %
# de margen para que el volante no golpee los topes en cada correccion.
# Del forzado saldria 65, y el volante se pasaria la carrera peleando.
#
# El +-20 que traia antes venia del servo de Arath (70..110 grados) y era
# solo el 36 % del recorrido de esta direccion: es otro mecanismo, ese
# numero nunca tuvo por que servir aqui.
#
# Estuvo un tiempo en 30, que era solo la mitad del recorrido disponible,
# y el volante se quedaba corto de angulo en pista. Despues en 45, puesto
# a ojo. Este 50.6 es el que calcula `check_hw.py topes` a partir de la
# medicion de arriba: es el valor medido, no estimado.
VOLANTE_LIMITE = 50.6

# Recorte por lado, como FRACCION de VOLANTE_LIMITE.
#
#   1.0  -> todo el tope disponible hacia ese lado
#   0.3  -> solo el 30 %
#   0.0  -> no gira nada hacia ese lado
#
# Van en fracciones y no en grados para que VOLANTE_LIMITE siga siendo el
# techo mecanico —el que sale de medir los topes— y estos dos sean el
# mando de ajuste. Cambiar el limite reescala los dos lados a la vez.
#
# Para que sirve: limitar cuanto se puede cerrar el robot hacia un lado
# sin tocar el otro. Afecta a TODO lo que mueve el volante, tanto el
# seguimiento de pared como el esquive con camara, porque el recorte se
# aplica en Robot.girar(), que es por donde pasan los dos.
#
# El signo lo fija VOLANTE_SIGNO: consigna positiva gira a la DERECHA.
VOLANTE_FRACCION_DERECHA = 1.0
VOLANTE_FRACCION_IZQUIERDA = 1.0

# Ganancia del seguimiento de pared: grados de volante por unidad de
# error crudo. Este es el mando principal para ajustar la agresividad.
#
# De donde venia: Arath hace map(error, -100, 100, -limites, +limites),
# donde la ganancia y el limite son el MISMO numero. Con el recorrido
# real de esta direccion eso daba 47.2/100 = 0.472, que es la respuesta
# equivalente a la suya. Se subio a 0.555, 1.2, 2, 3.0 y hasta 10; el 10
# se eligio cuando el error venia corrompido por un ultrasonico muerto que
# lo dejaba fijo en +62. Con los cinco sensores sanos el error real de
# operacion es de 5 a 9, y 10 saturaba el volante todo el tiempo. De ahi
# la bajada a 3, luego a 1.5, y de vuelta a 3 al subir la velocidad a 70:
# cuanto mas rapido va, menos tiempo tiene para corregir cada desvio y mas
# ganancia necesita para que la correccion llegue a tiempo.
VOLANTE_KP = 3                      # equivalente de Arath: 0.472

# Ganancia del seguimiento de pared DENTRO de la prueba de obstaculos.
#
# Va aparte de la de arriba a proposito. En la prueba abierta el robot
# solo tiene que centrarse entre paredes y le conviene ser agresivo; en
# la de obstaculos, el seguimiento de pared es lo que hace entre bloque y
# bloque, y una ganancia alta ahi lo deja bailando de pared a pared justo
# cuando la camara esta a punto de tomar el mando. Suele querer ser mas
# suave que la de la abierta.
#
# Arranca igualada a la de la abierta (1.5), que es la ya ajustada en
# pista. Es un numero suelto: bajarla aqui no toca a open_ard.py.
#
# Solo afecta al camino de los ultrasonicos. El esquive con camara tiene
# su propia ganancia, que sale de HUSKY_TARGET_* y del tope.
VOLANTE_KP_OBSTACULOS = 1.5

# Error crudo al que el volante llega al tope. No es un mando: sale de
# los dos valores de arriba y esta aqui para ver que significa el KP.
#
# Con KP 3 y tope 50.6 el volante satura con un error de 16.9. Para
# hacerse una idea: en un pasillo de 1 m, desviarse 10 cm del centro ya da
# un error de unos 40, porque los cuatro sensores laterales se mueven a la
# vez (dos se acercan y dos se alejan). O sea que el volante llega al tope
# a unos 4 cm de descentrado, y por debajo corrige de forma proporcional:
# hay banda de control de verdad, aunque estrecha.
# Si serpentea, bajar el KP es lo primero, antes que la velocidad.
VOLANTE_ERROR_TOPE = VOLANTE_LIMITE / VOLANTE_KP

# Sentido del volante. Verificado en el robot:
#
#   consigna positiva -> las ruedas giran a la DERECHA
#
# y eso es lo correcto, porque el error crudo es
# -(izquierda - derecha): si el robot se arrima a la pared izquierda, las
# distancias de la izquierda bajan, el error sale POSITIVO y el volante
# tiene que ir a la derecha para alejarse. Cierra.
#
# De paso cierra tambien el esquive de la camara: el verde lleva
# desplazamiento +100, o sea volante a la derecha, y asi el robot pasa por
# la derecha del bloque verde dejandolo a su izquierda, que es la regla.
VOLANTE_SIGNO = 1

# Correccion mecanica del centro, en grados de motor.
# En el programa de Arduino el factor 0.9 sobre un rango centrado en 90
# desplaza el centro a 81; eso es trim, no ganancia. Aqui va explicito.
# Notese que el camino de la camara no lleva ese 0.9.
VOLANTE_TRIM = 0.0

# Grados/s con que el volante corre hacia la consigna. El servo de Arath
# se mueve casi instantaneo; con 100 el motor tardaria 0.2 s en ir de
# centro a tope y el robot iria siempre corrigiendo tarde. El mediano
# llega a 1560, asi que 600 deja margen de sobra sin maltratar la
# direccion. Es de los primeros valores a ajustar en pista.
VOLANTE_VELOCIDAD = 600

# Si es True, al iniciar busca el centro chocando contra los topes.
# Con True, al arrancar busca los dos topes mecanicos y toma el punto
# medio como cero. Es lo correcto aqui: el recorrido libre medido es de
# 119 grados, o sea +-59.5, y VOLANTE_LIMITE es 50.6. Centrado de verdad,
# esos 50.6 caben a los dos lados; partiendo de un cero torcido, el
# volante chocaria contra un tope antes de llegar al limite por un lado
# y se quedaria corto por el otro, y eso en pista se confunde con un
# VOLANTE_TRIM mal puesto.
VOLANTE_AUTOCENTRAR = True
# Potencias con que busca los topes, en orden. Se recorren TODAS, de
# menor a mayor, y vale la posicion final.
#
# Medido en este robot: al 25 % la direccion no se mueve; al 40 % avanza
# 28 grados y se clava a mitad de camino; hace falta llegar al 100 % para
# tocar el tope de verdad. Por eso no basta con subir la potencia solo
# cuando el motor no arranca: hay que subirla siempre.
#
# Se empieza en 40 porque el 25 no mueve nada y solo gastaria tiempo.
VOLANTE_DUTIES_CENTRADO = (40, 70, 100)

# --------------------------------------------------------------------
# Traccion y recorrido
# --------------------------------------------------------------------

# Como se manda la traccion:
#
#   'velocidad' -> el numero es el % de la velocidad maxima del motor y
#                  el EV3 regula por encoder. Si la rueda se frena contra
#                  una imperfeccion de la pista, sube la potencia sola
#                  hasta recuperar la velocidad pedida.
#   'potencia'  -> el numero es el ciclo de trabajo, como el PWM de
#                  Arath. Lazo abierto: ante un obstaculo la potencia no
#                  cambia y el robot se queda clavado.
#
# Se cambio a 'velocidad' porque en pista el robot se frenaba con las
# imperfecciones. Arath no puede hacer esto: su motor no tiene encoder.
TRACCION_MODO = 'velocidad'

# De 0 a 100 en los dos modos. En 'velocidad' es el porcentaje de los
# 1560 grados/s que da el motor mediano, asi que 50 son 780 grados/s
# SOSTENIDOS, no "50 % de potencia y lo que salga".
#
# Cuanto mas rapido va, menos tiempo tiene el volante para corregir cada
# desvio: si empieza a serpentear, lo primero a bajar es VOLANTE_KP, no
# la velocidad.
VELOCIDAD = 70                      # prueba abierta

# Velocidad de la prueba de obstaculos. DESACOPLADA de la de arriba: aqui
# va mas lenta a proposito, porque la camara tiene que ver el bloque,
# decidir el lado y meter el rodeo completo antes de llegar a el. A la
# velocidad de la abierta llega encima del bloque sin haber terminado de
# esquivarlo.
#
# Arath tambien las tiene distintas (60 en la abierta, 40 en obstaculos).
#
# Igualada a 40, que es con la que se probo el esquive en pista con
# prueba_esquive.py. Estuvo en 35 antes de esas pruebas.
VELOCIDAD_OBSTACULOS = 40

ESQUINAS_META = 12                  # tres vueltas
ANGULO_ESQUINA = 87.0               # umbral de |anguloZ| para contar esquina

# Tiempo minimo entre dos esquinas, en segundos.
#
# Esto NO esta en el programa de Arath: es un anadido deliberado, y hace
# falta desde que la camara manda el volante.
#
# El problema medido: esquivando un bloque, el volante va al tope y el
# robot gira de verdad. El giroscopio no distingue ese giro del de una
# esquina de pista, acumula los 87 grados y suma una esquina que no
# existe. En una corrida de una vuelta salieron dos esquinas separadas
# por 1.1 segundos, cuando las reales iban cada 6.
#
# En obs_ard.py eso es un fallo de carrera: cada falsa adelanta la meta
# de 12 y el robot frena a mitad de pista creyendo que ya dio tres
# vueltas.
#
# 1.5 s deja fuera el caso medido con margen y queda muy por debajo de
# cualquier espaciado real: a la velocidad mas alta que se ha probado las
# esquinas caen cada 2 o 3 segundos.
ESQUINA_INTERVALO_MINIMO = 1.5
# Cuanto sigue avanzando despues de contar la esquina numero 12, antes de
# frenar. Durante esa media pasada sigue centrandose entre paredes con los
# ultrasonicos; no va a ciegas.
#
# Arath usa 200 ms. Aqui 500, para que el robot acabe de meterse en la
# zona de salida en vez de frenar justo al cruzar la ultima esquina.
MS_EXTRA_AL_FINAL = 500             # prueba abierta (Arath: 200)
MS_EXTRA_AL_FINAL_OBS = MS_EXTRA_AL_FINAL   # (Arath: 250)

PERIODO_LAZO = 0.02                 # 50 Hz maximo

# Telemetria de obs_ard.py por consola.
#
# Va limitada en frecuencia a proposito: el lazo corre a unos 40 Hz, y
# escribir 40 lineas por segundo por ssh sobre Bluetooth frena el propio
# lazo que se intenta medir. A 4 Hz se sigue leyendo bien y no estorba.
OBS_TELEMETRIA = True
OBS_TELEMETRIA_HZ = 4
