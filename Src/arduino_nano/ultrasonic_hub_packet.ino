#include <Wire.h>

#define I2C_ADDRESS 0x08
#define NUM_SENSORS 5
#define MAX_DISTANCE_CM 128
#define OUT_OF_RANGE_DISTANCE 125

// Five-sensor ultrasonic hub as an I2C slave, publishing whole frames.
//
// Superseded by ultrasonic_hub_serial.ino, which runs over USB instead.
// Kept because it is the fallback if the USB path is ever unavailable.
//
// An I2C frame is 8 bytes:
// [0..4] distance from each sensor, in cm
// [5]    validity mask (bits 0..4)
// [6]    frame counter
// [7]    XOR checksum of bytes 0..6
//
// The checksum and the frame counter are what make this readable over a
// noisy bus: the EV3 can reject a corrupt frame instead of acting on it,
// and can tell a fresh sweep from a repeated one.
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

  // Finish all five measurements before publishing a new frame.
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

  // Publish every field as one coherent snapshot. Interrupts are
  // disabled for the copy so an I2C request cannot land halfway through
  // and return a frame mixing two different sweeps.
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
