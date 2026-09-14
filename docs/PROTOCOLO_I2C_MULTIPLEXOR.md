# Protocolo I2C del multiplexor de cinco ultrasonicos

El Arduino Nano trabaja como esclavo I2C en la direccion `0x08`. En el bloque
Dexter esta direccion se introduce como `8`.

Cada lectura devuelve ocho bytes:

| Byte | Contenido |
|---:|---|
| 0 | Distancia del sensor 1 en cm |
| 1 | Distancia del sensor 2 en cm |
| 2 | Distancia del sensor 3 en cm |
| 3 | Distancia del sensor 4 en cm |
| 4 | Distancia del sensor 5 en cm |
| 5 | Mascara de validez; los bits 0 a 4 corresponden a los sensores 1 a 5 |
| 6 | Contador de trama, de 0 a 255 |
| 7 | Checksum XOR de los bytes 0 a 6 |

El valor `125` se usa como distancia de sustitucion cuando no hay eco o la
medicion queda fuera del rango configurado. Para distinguir un `125` real de un
fallo se debe consultar el bit correspondiente del byte de estado.

En EV3-G, el bloque `MUX_I2C_5` usa internamente `Read I2C 8 Bytes` de Dexter y
presenta los ocho campos como salidas numericas. Requiere tener importado el
paquete Dexter que contiene `readi2c_8b.vix`.

## Correccion de bytes negativos en Read I2C 1 Byte

Algunas versiones del bloque Dexter convierten directamente el byte recibido a
un numero con signo. Por eso un valor de `168` aparece en EV3-G como `-88`.
La conversion a byte sin signo es:

```text
si lectura < 0: lectura_corregida = lectura + 256
si lectura >= 0: lectura_corregida = lectura
```

El paquete `Dexter_I2C_Unsigned_Fix.ev3b` incorpora esta conversion dentro de
`Read I2C 1 Byte`. Tambien conserva el arreglo anterior de las entradas de
escritura para permitir valores de `0` a `255`.

Para validar una trama en EV3, calcule XOR sobre las primeras siete salidas y
compare el resultado con `CHECKSUM`. El contador `TRAMA` permite saber si el
Arduino termino un ciclo nuevo de cinco mediciones.
