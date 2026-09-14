#include <Wire.h>

#define I2C_ADDRESS 0x08
#define NUM_SENSORS 5
#define MAX_DISTANCE 128
#define OUT_OF_RANGE_DISTANCE 125

// 128 cm requieren unos 7424 us de ida y vuelta. Se deja un pequeno
// margen y se inicia una medicion nueva cada 9 ms.
#define ECHO_TIMEOUT_US ((MAX_DISTANCE * 58UL) + 500UL)
#define SENSOR_PERIOD_US 9000UL

// Orden confirmado de conexiones.
// Sensor:                       1   2   3   4   5
const byte trigPins[NUM_SENSORS] = {11, 9, 7, 5, 3};
const byte echoPins[NUM_SENSORS] = {12, 10, 8, 6, 4};

// Distancias que recibirá el EV3.
volatile byte distanceCm[NUM_SENSORS] = {
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE
};

// Sensor solicitado por el EV3: 1, 2, 3, 4 o 5.
volatile byte requestedSensor = 1;

byte readUltrasonic(byte trigPin, byte echoPin);
void receiveEvent(int numberOfBytes);
void requestEvent();

void setup()
{
  // Configurar los cinco sensores.
  for (byte i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
    digitalWrite(trigPins[i], LOW);
  }

  // Arduino Nano como esclavo I2C.
  Wire.begin(I2C_ADDRESS);
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestEvent);
}

void loop()
{
  // Leer los cinco sensores uno por uno.
  for (byte i = 0; i < NUM_SENSORS; i++) {
    unsigned long measurementStart = micros();

    byte value = readUltrasonic(
      trigPins[i],
      echoPins[i]
    );

    // Es una variable de un byte, por lo que la actualización
    // es atómica en el Arduino Nano.
    distanceCm[i] = value;

    // Mantener una separacion minima entre disparos para reducir ecos
    // cruzados, sin imponer los 70 ms anteriores a cada sensor.
    unsigned long elapsed = micros() - measurementStart;
    if (elapsed < SENSOR_PERIOD_US) {
      delayMicroseconds((unsigned int)(SENSOR_PERIOD_US - elapsed));
    }
  }
}

byte readUltrasonic(byte trigPin, byte echoPin)
{
  // Preparar TRIG.
  digitalWrite(trigPin, LOW);
  delayMicroseconds(3);

  // Pulso de disparo.
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Esperar el pulso ECHO.
  unsigned long duration =
    pulseIn(echoPin, HIGH, ECHO_TIMEOUT_US);

  // No se recibió ningún eco.
  if (duration == 0) {
    return OUT_OF_RANGE_DISTANCE;
  }

  // Convertir microsegundos a centímetros.
  unsigned int distance = duration / 58UL;

  if (distance == 0) {
    return OUT_OF_RANGE_DISTANCE;
  }

  // Todo lo que esté a 128 cm o más usa 128 como valor de saturación.
  if (distance > MAX_DISTANCE) {
    distance = OUT_OF_RANGE_DISTANCE;
  }

  return (byte)distance;
}

// El EV3 escribe qué sensor desea leer.
void receiveEvent(int numberOfBytes)
{
  if (Wire.available()) {
    byte command = Wire.read();

    if (command >= 1 && command <= 5) {
      requestedSensor = command;
    }
  }

  // Vaciar cualquier byte adicional.
  while (Wire.available()) {
    Wire.read();
  }
}

// El EV3 solicita un byte con la distancia.
void requestEvent()
{
  byte sensor = requestedSensor;
  byte value = 0;

  if (sensor >= 1 && sensor <= 5) {
    value = distanceCm[sensor - 1];
  }

  Wire.write(value);
}
