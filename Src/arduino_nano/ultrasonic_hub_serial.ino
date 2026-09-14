// Multiplexor de cinco ultrasonicos que habla por USB en vez de I2C.
//
// El Nano se conecta con su propio cable USB al puerto USB del ladrillo
// EV3. En ev3dev aparece como /dev/ttyUSB0 (chip CH340) o /dev/ttyACM0.
//
// Ventaja sobre la version I2C: el I2C de los puertos de sensores del EV3
// es por software y va a pocos kHz. A 115200 baudios sobra ancho de banda
// y ademas se libera un puerto de sensores.
//
// Formato de linea, ASCII terminado en \n:
//
//   U d1 d2 d3 d4 d5 mascara trama checksum
//
//   d1..d5    distancia de cada sensor en cm
//   mascara   bits 0..4, uno por sensor: 1 = medicion valida
//   trama     contador de barridos completos, 0..255
//   checksum  XOR de los siete numeros anteriores
//
// Se imprime una linea despues de CADA sensor, no de cada barrido, para
// que el EV3 siempre tenga el dato mas fresco posible. Son unas 110
// lineas por segundo.

#define NUM_SENSORS 5
#define MAX_DISTANCE_CM 128
#define OUT_OF_RANGE_DISTANCE 125
#define BAUD 115200

#define ECHO_TIMEOUT_US ((MAX_DISTANCE_CM * 58UL) + 500UL)
#define SENSOR_PERIOD_US 9000UL

// Mismo cableado que las versiones I2C.
const byte trigPins[NUM_SENSORS] = {11, 9, 7, 5, 3};
const byte echoPins[NUM_SENSORS] = {12, 10, 8, 6, 4};

byte distanceCm[NUM_SENSORS] = {
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE
};

byte validMask = 0;
byte frameCounter = 0;

byte readUltrasonic(byte trigPin, byte echoPin, bool &valid);
void sendFrame();

void setup()
{
  for (byte i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
    digitalWrite(trigPins[i], LOW);
  }

  Serial.begin(BAUD);
}

void loop()
{
  for (byte i = 0; i < NUM_SENSORS; i++) {
    unsigned long measurementStart = micros();
    bool valid = false;

    distanceCm[i] = readUltrasonic(trigPins[i], echoPins[i], valid);

    if (valid) {
      validMask |= (byte)(1U << i);
    } else {
      validMask &= (byte)~(1U << i);
    }

    sendFrame();

    // Separacion minima entre disparos para no arrastrar ecos cruzados.
    unsigned long elapsed = micros() - measurementStart;
    if (elapsed < SENSOR_PERIOD_US) {
      delayMicroseconds((unsigned int)(SENSOR_PERIOD_US - elapsed));
    }
  }

  frameCounter++;
}

byte readUltrasonic(byte trigPin, byte echoPin, bool &valid)
{
  valid = false;

  digitalWrite(trigPin, LOW);
  delayMicroseconds(3);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration = pulseIn(echoPin, HIGH, ECHO_TIMEOUT_US);

  if (duration == 0) {
    return OUT_OF_RANGE_DISTANCE;
  }

  unsigned int distance = duration / 58UL;

  if (distance == 0 || distance > MAX_DISTANCE_CM) {
    return OUT_OF_RANGE_DISTANCE;
  }

  valid = true;
  return (byte)distance;
}

void sendFrame()
{
  byte checksum = 0;
  for (byte i = 0; i < NUM_SENSORS; i++) {
    checksum ^= distanceCm[i];
  }
  checksum ^= validMask;
  checksum ^= frameCounter;

  Serial.print('U');
  for (byte i = 0; i < NUM_SENSORS; i++) {
    Serial.print(' ');
    Serial.print(distanceCm[i]);
  }
  Serial.print(' ');
  Serial.print(validMask);
  Serial.print(' ');
  Serial.print(frameCounter);
  Serial.print(' ');
  Serial.println(checksum);
}
