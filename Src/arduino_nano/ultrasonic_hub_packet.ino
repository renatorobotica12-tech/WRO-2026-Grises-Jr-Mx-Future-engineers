#include <Wire.h>

#define I2C_ADDRESS 0x08
#define NUM_SENSORS 5
#define MAX_DISTANCE_CM 128
#define OUT_OF_RANGE_DISTANCE 125

// Una trama I2C ocupa 8 bytes:
// [0..4] distancia de cada sensor en cm
// [5]    mascara de validez (bits 0..4)
// [6]    contador de trama
// [7]    checksum XOR de los bytes 0..6
#define PACKET_SIZE 8

#define ECHO_TIMEOUT_US ((MAX_DISTANCE_CM * 58UL) + 500UL)
#define SENSOR_PERIOD_US 9000UL

const byte trigPins[NUM_SENSORS] = {11, 9, 7, 5, 3};
const byte echoPins[NUM_SENSORS] = {12, 10, 8, 6, 4};

volatile byte distanceCm[NUM_SENSORS] = {
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE
};

volatile byte validMask = 0;
volatile byte frameCounter = 0;

byte readUltrasonic(byte trigPin, byte echoPin, bool &valid);
void requestEvent();

void setup()
{
  for (byte i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
    digitalWrite(trigPins[i], LOW);
  }

  Wire.begin(I2C_ADDRESS);
  Wire.onRequest(requestEvent);
}

void loop()
{
  byte nextDistances[NUM_SENSORS];
  byte nextValidMask = 0;

  // Completar las cinco mediciones antes de publicar una trama nueva.
  for (byte i = 0; i < NUM_SENSORS; i++) {
    unsigned long measurementStart = micros();
    bool valid = false;

    nextDistances[i] = readUltrasonic(trigPins[i], echoPins[i], valid);
    if (valid) {
      nextValidMask |= (byte)(1U << i);
    }

    unsigned long elapsed = micros() - measurementStart;
    if (elapsed < SENSOR_PERIOD_US) {
      delayMicroseconds((unsigned int)(SENSOR_PERIOD_US - elapsed));
    }
  }

  // Publicar todos los campos como una instantanea coherente.
  noInterrupts();
  for (byte i = 0; i < NUM_SENSORS; i++) {
    distanceCm[i] = nextDistances[i];
  }
  validMask = nextValidMask;
  frameCounter++;
  interrupts();
}

byte readUltrasonic(byte trigPin, byte echoPin, bool &valid)
{
  digitalWrite(trigPin, LOW);
  delayMicroseconds(3);
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  unsigned long duration = pulseIn(echoPin, HIGH, ECHO_TIMEOUT_US);
  if (duration == 0) {
    valid = false;
    return OUT_OF_RANGE_DISTANCE;
  }

  unsigned int distance = duration / 58UL;
  if (distance == 0 || distance > MAX_DISTANCE_CM) {
    valid = false;
    return OUT_OF_RANGE_DISTANCE;
  }

  valid = true;
  return (byte)distance;
}

void requestEvent()
{
  byte packet[PACKET_SIZE];
  byte checksum = 0;

  for (byte i = 0; i < NUM_SENSORS; i++) {
    packet[i] = distanceCm[i];
  }
  packet[5] = validMask;
  packet[6] = frameCounter;

  for (byte i = 0; i < PACKET_SIZE - 1; i++) {
    checksum ^= packet[i];
  }
  packet[7] = checksum;

  Wire.write(packet, PACKET_SIZE);
}
