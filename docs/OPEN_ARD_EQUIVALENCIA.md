# OPEN_ARD: replica en EV3 del programa Arduino de la prueba abierta

Archivo nuevo: `ev3/WRO 26 OPEN ARD.ev3`, programa `OPEN_ARD`.

Es una copia completa del proyecto `ev3/WRO 26.ev3` mas un programa adicional.
El proyecto original no se modifico. Los unicos cambios respecto de el son:

- se agrego el archivo `OPEN_ARD.ev3p`;
- en `Project.lvprojx` se registro ese archivo y se declaro la variable global `ESQUINAS`.

Todos los demas programas y bloques (`OPEN`, `OBSTACULOS`, `ESTACIONAMIENTO`,
`PID_R_20`, `ARD`, `ERROR`, `INICIO`, los bloques IMU, etc.) siguen exactamente
igual.

## Origen

Se replico la pagina activa de `WRO Arath Nacional/mind+/WRO OPEN ARD-UNO.mp`
(Arduino UNO). Ese programa es:

```
Inicio:
  limites = 20
  esquinas = 0
  MPU6050 en 0x68: preparar, iniciar, calibrar con 600 muestras

Bucle:
  actualizar IMU
  zona muerta 0.3
  Distancia()
  Motor(velocidad)
  Volante(error * 0.9)
  si anguloZ >= 87 o anguloZ <= -87:
      reiniciar angulos
      esquinas = esquinas + 1
  si esquinas >= 12:
      tiempo = millis() + 200
      repetir hasta millis() >= tiempo: Distancia(); Motor(velocidad); Volante(error*0.9)
      velocidad = 0
  si no:
      velocidad = 60
  LEDs WS2812 segun esquinas == 4 / 8 / 12

Distancia():
  25izq   = ultrasonico(trig 4,  echo 5)
  frontal = ultrasonico(trig 4,  echo 6)      <- se lee pero no se usa
  25der   = ultrasonico(trig 4,  echo 7)
  90izq   = ultrasonico(trig 13, echo 2)
  90der   = ultrasonico(trig 13, echo 3)
  error   = map( ((90izq + 25izq) - (25der + 90der)) * -1, -100, 100, 70, 110 )

Motor(v):    pin9 LOW, pin10 HIGH, PWM pin11 = map(v, 0,100, 0,255)
Volante(a):  servo pin 8 = a
```

## Equivalencias

| Arduino | EV3 |
|---|---|
| `Inicio` (limites, serial, reset) | bloque `INICIO` (reinicia volante, encoders B y C, `SUMA`, `LINEAS`, pantalla, LED) |
| `esquinas = 0` | `ESQUINAS = 0` (variable global nueva) |
| `velocidad = 60` | `VEL = 60` antes del bucle |
| `mpu.calibrar(600)` | `IMU_Calibrar_WRO` puerto 1.2, direccion 34, temporizador 8 |
| `Distancia()` + calculo de `error` | bloque `ERROR`, que lee `ARD` indices 1, 2, 4, 5 y hace `(izq1+izq2) - (der1+der2)` |
| `Volante(error * 0.9)` | `PID_R_20` con `Entrada Numero = ERROR`, KP 0.3, KI 0, KD 0, POTENCIAMAX 30, LIM 20 |
| `Motor(velocidad)` | `MotorUnlimited` puerto 1.D con potencia leida de `VEL` |
| `actualizar` + `angulo(Z)` | `IMU_Giro_WRO` puerto 1.2, direccion 34, temporizador 8, Reiniciar = falso, salida **Grados** |
| `anguloZ >= 87 o <= -87` | `valor absoluto(Grados) >= 87` |
| `reiniciarAngulos()` | `IMU_Giro_WRO` con **Reiniciar = verdadero** dentro del caso verdadero |
| `esquinas = esquinas + 1` | leer `ESQUINAS`, sumar 1, escribir `ESQUINAS` |
| `esquinas >= 12` -> salir | comparacion `ESQUINAS >= 12` conectada a **Detener si verdadero** del bucle |
| avanzar 200 ms mas y `velocidad = 0` | esperar 0.2 s, luego `MotorStop` 1.D, `MediumMotorStop` 1.B, `VEL = 0`, `reinicio_volante` |

## Diferencias deliberadas

**Servo contra PID.** En Arduino el volante es un servo: `error` ya sale mapeado
a 70..110 grados y luego se multiplica por 0.9. El EV3 mueve el volante con el
motor mediano B a traves de `PID_R_20`, que recibe el error crudo. Por eso no se
copian ni el `map` ni el factor 0.9: se usan las ganancias que ya estaban
probadas en el programa `OPEN` existente (KP 0.3, KI 0, KD 0, POTENCIAMAX 30,
LIM 20). Es el punto a ajustar en pista.

Nota sobre el original: `error` mapeado a 70..110 y luego multiplicado por 0.9 da
63..99, es decir centro 81 y no 90. Si en el robot de Arduino el volante queda
recto, ese 0.9 esta actuando como compensacion mecanica, no como ganancia.

**Zona muerta.** `zonaMuerta(0.3)` es de la extension MPU6050 de Mind+. El bloque
`IMU_Giro_WRO` del AbsoluteIMU ya trae su propia correccion de cero por
calibracion, asi que no se replico.

**LEDs WS2812.** No hay tira de LEDs en el EV3, asi que el indicador de vuelta
(4, 8, 12 esquinas) no se replico. Si lo quieren, el equivalente natural es
mostrar `ESQUINAS` en la pantalla del ladrillo con un bloque de texto.

**Frontal.** El ultrasonico frontal se lee en Arduino pero no se usa en ninguna
decision, asi que en EV3 no se lee.

**MPU6050 contra AbsoluteIMU.** Arduino usa MPU6050 en 0x68 por I2C directo; el
EV3 usa el mindsensors AbsoluteIMU en el puerto 2, direccion 34 (0x22).

## Hardware que asume el programa

- Puerto de sensores **2**: mindsensors AbsoluteIMU (direccion I2C 34).
- Puerto de sensores **4**: Arduino Nano multiplexor de ultrasonicos (direccion I2C 8), leido por el bloque `ARD`.
- Puerto de motores **B**: motor mediano del volante (lo maneja `PID_R_20`).
- Puerto de motores **D**: motor de traccion.

## Para probar

1. Abrir `ev3/WRO 26 OPEN ARD.ev3` en LEGO MINDSTORMS Education EV3.
2. Abrir el programa `OPEN_ARD`.
3. Dejar el robot inmovil hasta que termine `IMU_Calibrar_WRO`; si se mueve, el
   cero del giroscopio queda mal y el conteo de esquinas falla.
4. Verificar el sentido de giro: si al girar a la derecha **Grados** baja en vez
   de subir, no importa para el conteo porque se compara el valor absoluto, pero
   si importa para el signo del error del PID.
5. Ajustar KP y POTENCIAMAX del bloque `PID_R_20` dentro del bucle.
