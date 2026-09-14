# Bloque de giro para mindsensors AbsoluteIMU-ACG y EV3

El proyecto `ev3/WRO 26 I2C MULTI IMU.ev3` contiene el bloque personalizado **IMU_ANGULO**. Este bloque convierte la velocidad angular del eje Z en:

- **Z corregida:** velocidad de giro en grados por segundo.
- **GRADOS:** giro acumulado con signo; no se limita a 0–360.
- **VUELTAS:** giro acumulado dividido entre 360.

## Conexión recomendada

Monte el AbsoluteIMU plano y firme, con el eje Z perpendicular al piso. Conecte el sensor directamente a un puerto de sensores EV3 (1–4); no lo conecte al multiplexor de ultrasonidos.

En EV3-G, use el bloque oficial **Mindsensors-ABSIMU**, modo **Read Gyro**, y conecte su salida **Z Gyro** a la entrada **Z del sensor** de `IMU_ANGULO`.

Los datos del bloque oficial están en mili-grados por segundo. Por ello:

- **ESCALA = 0.001** con el bloque oficial Mindsensors-ABSIMU.
- **ESCALA = 1** si la lectura que entra ya está en grados por segundo, por ejemplo con el bloque Dexter corregido incluido en esta carpeta.
- **TIMER = 8** de forma predeterminada. No use el temporizador 8 en otra parte del programa mientras esté contando el giro.

## Uso

1. Deje inmóvil el robot al iniciar.
2. Lea varias veces `Z Gyro` durante uno o dos segundos y calcule el promedio. Escriba ese promedio en **OFFSET**. Si en reposo entrega aproximadamente cero, empiece con `OFFSET = 0`.
3. Antes de empezar el recorrido, llame una vez a `IMU_ANGULO` con **REINICIAR = verdadero**. Esta llamada pone GRADOS y VUELTAS en cero y prepara el temporizador.
4. Dentro del bucle principal, lea primero **Z Gyro** y después llame a `IMU_ANGULO` con **REINICIAR = falso**.
5. Use **GRADOS** para giros como 90°, 180° o 720°. Use **VUELTAS** si resulta más cómodo: 1 vuelta = 360°, 2.5 vueltas = 900°.

No agregue un bloque de espera largo dentro de este lazo. El bloque mide el tiempo real transcurrido con el temporizador EV3, de modo que sigue contando aunque el periodo del lazo varíe.

## Sentido del giro

El signo depende de la orientación física del sensor. Si al girar a la derecha los grados disminuyen y desea que aumenten, cambie **ESCALA** a `-0.001` (bloque oficial) o `-1` (lectura ya expresada en grados/s).

## Precisión para WRO

El giroscopio acumula cualquier pequeño error de offset. Calibre con el robot totalmente quieto, evite vibraciones y reinicie el contador justo antes de cada maniobra o tramo. Para giros cortos y repetibles conviene frenar unos grados antes del objetivo y terminar a menor velocidad.

La brújula del AbsoluteIMU puede ayudar a corregir deriva a largo plazo, pero cerca de motores, cables de potencia y estructuras metálicas suele sufrir interferencias; para contar vueltas completas el acumulador del giroscopio es la opción principal.
