# Programa de Arath portado a ev3dev

Version en Python de los dos programas Arduino de Arath, corriendo sobre
el ladrillo EV3. No reemplaza a los programas EV3-G del proyecto `ev3/`;
es un camino paralelo.

## Por que ev3dev y no EV3-G

El programa de Arath es codigo, no bloques. En EV3-G hubo que aproximarlo
(ver `documentos/OPEN_ARD_EQUIVALENCIA.md`): el `map` y el factor 0.9 se
cambiaron por el bloque `PID_R_20`, la zona muerta se omitio y el conteo
de esquinas se rehizo con bloques. En ev3dev cada una de esas piezas se
escribe tal cual, y ademas se puede leer el Nano por USB en vez de por el
I2C lento de los puertos de sensores.

## Cableado

Confirmado en el robot con `check_hw.py puertos`:

| Puerto | Dispositivo | Como lo ve ev3dev |
|---|---|---|
| Sensor 2 | mindsensors AbsoluteIMU | `ms-absolute-imu` en `ev3-ports:in2:i2c17` |
| Sensor 3 | HuskyLens por el adaptador OFDL | `ev3-uart-84` |
| USB del ladrillo | Arduino Nano, cinco ultrasonicos | `/dev/ttyUSB0` |
| Motor A | volante | `lego-ev3-m-motor` |
| Motor B | traccion | `lego-ev3-m-motor` |

Los puertos de sensores 1 y 4 y los de motores C y D quedan libres.

Dos cosas no coinciden con `documentos/OPEN_ARD_EQUIVALENCIA.md`, que
describia el montaje de EV3-G:

- la traccion **no** es un motor grande en D, sino un **mediano en B**;
- el volante **no** esta en B sino en **A**.

Por eso `robot.py` usa la clase generica `Motor` y no `LargeMotor` ni
`MediumMotor`: esas dos filtran por `driver_name` y `LargeMotor` revienta
con un motor mediano. Nada de lo que hace ese archivo depende del tamano
del motor.

### El Nano por USB

Se le carga el firmware nuevo
[`arduino_nano/ultrasonic_hub_serial`](../arduino_nano/ultrasonic_hub_serial/ultrasonic_hub_serial.ino)
y se conecta con su propio cable USB al puerto USB del ladrillo. El
cableado de los ultrasonicos no cambia: mismos pines trig y echo.

Manda lineas ASCII a 115200 baudios:

```
U d1 d2 d3 d4 d5 mascara trama checksum
```

Una linea despues de **cada** sensor, no de cada barrido, para que el EV3
siempre tenga el dato mas fresco. Son unas 110 lineas por segundo. El EV3
descarta las viejas y se queda con la ultima completa.

Por que asi y no por I2C: el I2C de los puertos de sensores del EV3 no es
hardware, lo genera por software y va a pocos kHz. Ademas libera un
puerto de sensores y deja los pines A4 y A5 del Nano libres.

### La HuskyLens

El adaptador de OFDL Robotics no expone la camara por I2C: lleva un
Arduino Pro Mini que traduce los datos al **protocolo LEGO UART**. Para
el EV3 es un sensor LEGO cualquiera, asi que **ev3dev lo detecta solo**.
No hay que tocar el modo del puerto ni cargar drivers, a diferencia del
Nano en I2C.

**Ojo con el orden de los valores: el README del adaptador no coincide
con lo que entrega de verdad.** Ahi dice seis valores en el orden
`State, ID, X, Y, W, H`. Medido en el robot son **ocho** valores s32 y el
orden es otro:

```
0 X   1 Y   2 W   3 H   4 ID   5 State   6 y 7 siempre 0
```

Se confirma mirando el indice 5: alterna entre 1 y 7, que son justo los
codigos de "objeto detectado" y "no ve ninguno", y cuando vale 7 todos
los demas se van a cero.

`husky.py` lee `bin_data` en vez de ocho `value(i)`: es una sola lectura
atomica de 32 bytes, asi que no mezcla datos de dos fotogramas, y tarda
5 ms en vez de 49 ms. A 49 ms la camara sola dejaria el lazo en 20 Hz.

Codigos de State del adaptador:

| Codigo | Significado |
|---:|---|
| 9 | adaptador conectado pero HuskyLens no |
| 8 | conectada, sin objetos aprendidos |
| 7 | conectada y con objetos aprendidos, no ve ninguno |
| 1 | hay objeto detectado |
| 0 | puerto desconectado o perdida de datos |

`obs_ard.py` imprime este estado al arrancar, antes de calibrar.

## Estructura

Solo se corren tres archivos. La carpeta `wro/` es una biblioteca: los
programas la importan, pero **no se ejecuta nada de adentro**, igual que
los bloques `ARD` o `PID_R_20` de EV3-G existen para que los programas
los llamen y no para correrlos sueltos.

```
ev3dev/
  check_hw.py        SE CORRE  diagnostico; primero que nada
  open_ard.py        SE CORRE  prueba abierta, tres vueltas
  obs_ard.py         SE CORRE  prueba de obstaculos

  wro/               no se corre nada de aqui
    config.py        se EDITA: puertos, cableado y ganancias
    robot.py         traccion y volante
    imu.py           AbsoluteIMU e integracion del angulo
    ultrasonics.py   Nano, por USB o por I2C
    husky.py         HuskyLens por el adaptador OFDL
    ports.py         modos I2C de los puertos de sensores
    i2c.py           acceso I2C crudo
    util.py          map y constrain de Arduino
```

De esos tres, `check_hw.py` no mueve el robot salvo en el comando
`volante`: solo lee sensores e imprime. Es el que se usa para llenar
`wro/config.py`. Los otros dos son las carreras.

## Instalacion

En el ladrillo, con ev3dev ya arrancado:

```bash
sudo pip3 install pyserial smbus2
```

`smbus2` solo hace falta si dejan el Nano en I2C (`ARD_BACKEND = 'i2c'`).

Copiar la carpeta al ladrillo conservando el nombre, para que quede
`~/ev3dev/check_hw.py` y `~/ev3dev/wro/config.py`:

```bash
scp -r ev3dev robot@ev3dev.local:~/ev3dev
```

Dar permiso de ejecucion:

```bash
chmod +x ~/ev3dev/*.py
```

Todos los comandos de aqui en adelante se corren parados en esa carpeta:

```bash
cd ~/ev3dev
```

Los archivos deben conservar finales de linea LF. Si al correrlos sale
`bad interpreter`, es eso.

Si al abrir el puerto serie sale permiso denegado:

```bash
sudo usermod -a -G dialout robot
```

## Antes de la primera corrida

Hay varias cosas que solo se pueden medir en el robot. `check_hw.py` las
resuelve una por una.

```bash
python3 check_hw.py puertos
```

Lista puertos, drivers, buses I2C, puertos serie y motores. Confirma que
el AbsoluteIMU aparece como `ms-absolute-imu`, que la HuskyLens aparece
en el puerto 3 como sensor UART y que existe `/dev/ttyUSB0`.

```bash
python3 check_hw.py serie
```

Lineas crudas del Nano. Separa un problema de cable de uno de formato.

```bash
python3 check_hw.py ultra
```

Trama ya interpretada, en vivo.

```bash
python3 check_hw.py mapear
```

Averigua solo que indice es cada ultrasonico: toma una linea base con
todo despejado y despues pide acercar la mano a uno por uno. Al final
imprime `IDX_IZQ`, `IDX_FRONTAL` e `IDX_DER` listos para pegar. La mano
va a unos 10 cm, no pegada al sensor: demasiado cerca no hay eco y el
firmware devuelve 125, que confunde la medicion.

```bash
python3 check_hw.py husky
```

Imprime el driver, la lista de modos y los seis valores en vivo. Resuelve
tres cosas: que poner en `HUSKY_MODO` (ev3dev llama a los modos `MODE0`,
`MODE1`... porque no conoce este sensor), en que rango vienen X e Y para
ajustar `HUSKY_CENTRO_X` y `HUSKY_CENTRO_Y`, y que ID le toca a cada
color para `HUSKY_ID_A` y `HUSKY_ID_B`. Pongan un bloque de cada color
delante de la camara y anoten el ID.

```bash
python3 check_hw.py escala
```

Calcula `IMU_ESCALA`: integra la lectura cruda mientras usted gira el
robot noventa grados a mano. Si sale negativo, dejenlo negativo.

La magnitud ya esta resuelta sin mover nada: el driver reporta
`units = d/s` y `decimals = 1`, o sea que el entero crudo viene
multiplicado por diez, y por eso `IMU_ESCALA = 0.1`. No es el 0.001 de
EV3-G, donde el bloque oficial si entrega mili-grados/s. Lo que falta
confirmar con este comando es **el signo**.

```bash
python3 check_hw.py motores
```

Mueve 15 grados un motor a la vez, con aviso antes de cada uno, para
confirmar cual es la traccion y cual el volante. Levanten el robot o
ponganlo sobre un soporte.

```bash
python3 check_hw.py volante
```

Manda el volante a los dos topes logicos, para fijar `VOLANTE_SIGNO`.

## Correr

```bash
python3 open_ard.py
```

```bash
python3 obs_ard.py
```

Los dos: centran el volante, calibran el giroscopio con el robot inmovil,
esperan el boton central, corren las tres vueltas y frenan. El boton de
retroceso detiene todo en cualquier momento.

## Equivalencias con los programas de Arath

| Arduino / Mind+ | ev3dev |
|---|---|
| `mpu.prepararFacil` + `iniciar` + `calibrar(600)` | `Giroscopio.calibrar()` |
| `actualizar` + `zonaMuerta(0.3)` | `Giroscopio.actualizar()` |
| `angulo(Z)` / `reiniciarAngulos()` | `Giroscopio.grados` / `.reiniciar()` |
| cinco `readUltrasound` | `hub.actualizar()` |
| `map(((90i+25i)-(25d+90d))*-1, ...)` | `error_crudo()` por `VOLANTE_KP` |
| `Volante(error * 0.9)` | `Robot.girar_por_error()` |
| `Motor(velocidad)` | `Robot.avanzar()` |
| `millis()` | `time.time()` |
| `3 vueltas %n` | conteo de esquinas dentro del lazo de `obs_ard.py` |
| `actualizar Huskylens` | `HuskyLens.actualizar()` |
| `ERROR CAM = constrain(map(X+-100, ...))` | `HuskyLens.angulo_esquive()` |
| `huskylens.writeOSD` | telemetria por consola, `OBS_TELEMETRIA` |
| tira WS2812 segun esquinas | LEDs del ladrillo, `indicar_vuelta()` |

El esquive con camara se verifico numericamente: para todo X de 0 a 320 y
los dos IDs, `angulo_esquive()` da exactamente el mismo angulo que la
formula de Mind+, una vez trasladado el centro de 90 a 0.

## Diferencias deliberadas

**El factor 0.9.** En el original el error ya sale mapeado a 70..110 y
despues se multiplica por 0.9, lo que deja el rango en 63..99 y el centro
en 81, no en 90. Si el robot de Arath va recto con eso, ese 0.9 compensa
un desalineado mecanico del servo. Por eso se separo en `VOLANTE_KP`
(ganancia) y `VOLANTE_TRIM` (centro), que empieza en 0. Notese que el
camino de la camara **no** lleva ese 0.9, lo cual refuerza que era trim.

**Que bloque mira la camara.** Arath pide los dos primeros recuadros de
la HuskyLens y se queda con el mas ancho, y usa el indice del recuadro
como si fuera el color. El adaptador OFDL devuelve **un solo** recuadro
por lectura, pero devuelve su **ID aprendido de verdad**, que es mas
confiable que el indice. Lo que se pierde es el criterio de "el mas
ancho" cuando hay dos bloques a la vista a la vez. Hay que ver en pista
si el recuadro que entrega el adaptador es el mas grande o simplemente el
primero; `check_hw.py husky` con dos bloques delante lo resuelve en un
minuto.

**Llamadas repetidas.** El original llama a `actualizar Huskylens` tres
veces por vuelta de lazo y a `Actualizar Distancia` dos. Es ruido de
programacion por bloques; aqui se lee cada sensor una sola vez por vuelta.

**El sensor frontal.** Arath lo lee y no lo usa en ninguna decision. Aqui
se lee igual porque viene gratis en la misma trama, y queda en
`hub.frontal` para cuando haga falta.

## Lo que falta probar en pista

- Confirmar `IMU_ESCALA` y su signo.
- Confirmar los indices de los cinco ultrasonicos.
- Confirmar el ID de cada color en la HuskyLens.
- Medir cuantas vueltas de lazo por segundo salen de verdad. Los dos
  programas reportan al final cuantas tramas leyeron y cuantas salieron
  mal.
- Ajustar `VOLANTE_KP` y `HUSKY_DESPLAZAMIENTO_PX`: ese ultimo es cuanto
  se abre el rodeo alrededor del bloque.
