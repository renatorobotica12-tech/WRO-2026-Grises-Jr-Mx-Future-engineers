// Five-sensor ultrasonic hub as an I2C slave, one byte per request.
//
// This is the oldest of the three firmwares. The EV3 writes which sensor
// it wants, then reads back a single distance byte, so a full set of
// five readings costs five I2C transactions.
//
// Superseded twice over: ultrasonic_hub_packet.ino returns all five in
// one 8-byte frame with a checksum, and ultrasonic_hub_serial.ino drops
// I2C altogether and streams over USB. Kept for reference.

#include <Wire.h>

#define I2C_ADDRESS 0x08
#define NUM_SENSORS 5
#define MAX_DISTANCE 128
#define OUT_OF_RANGE_DISTANCE 125

// 128 cm takes about 7424 us there and back. A small margin is added,
// and a new measurement is started every 9 ms.
#define ECHO_TIMEOUT_US ((MAX_DISTANCE * 58UL) + 500UL)
#define SENSOR_PERIOD_US 9000UL

// Confirmed wiring order.
// Sensor:                       1   2   3   4   5
const byte trigPins[NUM_SENSORS] = {11, 9, 7, 5, 3};
const byte echoPins[NUM_SENSORS] = {12, 10, 8, 6, 4};

// The distances the EV3 will read.
volatile byte distanceCm[NUM_SENSORS] = {
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE,
  OUT_OF_RANGE_DISTANCE
};

// Which sensor the EV3 asked for: 1, 2, 3, 4 or 5.
volatile byte requestedSensor = 1;

byte readUltrasonic(byte trigPin, byte echoPin);
void receiveEvent(int numberOfBytes);
void requestEvent();

void setup()
{
  // Set up all five sensors.
  for (byte i = 0; i < NUM_SENSORS; i++) {
    pinMode(trigPins[i], OUTPUT);
    pinMode(echoPins[i], INPUT);
    digitalWrite(trigPins[i], LOW);
  }

  // The Nano acts as an I2C slave.
  Wire.begin(I2C_ADDRESS);
  Wire.onReceive(receiveEvent);
  Wire.onRequest(requestEvent);
}

void loop()
{
  // Read the five sensors one at a time.
  for (byte i = 0; i < NUM_SENSORS; i++) {
    unsigned long measurementStart = micros();

    byte value = readUltrasonic(
      trigPins[i],
      echoPins[i]
    );

    // A single-byte variable, so the update is atomic on the Nano and
    // an I2C interrupt cannot catch it half written.
    distanceCm[i] = value;

    // Keep a minimum spacing between triggers to reduce cross-talk
    // between sensors, without imposing the old 70 ms on each one.
    unsigned long elapsed = micros() - measurementStart;
    if (elapsed < SENSOR_PERIOD_US) {
      delayMicroseconds((unsigned int)(SENSOR_PERIOD_US - elapsed));
    }
  }
}

byte readUltrasonic(byte trigPin, byte echoPin)
{
  // Settle TRIG low first.
  digitalWrite(trigPin, LOW);
  delayMicroseconds(3);

  // Trigger pulse.
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);

  // Wait for the ECHO pulse.
  unsigned long duration =
    pulseIn(echoPin, HIGH, ECHO_TIMEOUT_US);

  // No echo came back.
  if (duration == 0) {
    return OUT_OF_RANGE_DISTANCE;
  }

  // Microseconds to centimetres.
  unsigned int distance = duration / 58UL;

  if (distance == 0) {
    return OUT_OF_RANGE_DISTANCE;
  }

  // Anything at 128 cm or beyond reports the out-of-range sentinel.
  //
  // Note this firmware has no validity mask, so the EV3 cannot tell a
  // real 125 cm reading from a missing echo. That is the main reason the
  // later firmwares exist.
  if (distance > MAX_DISTANCE) {
    distance = OUT_OF_RANGE_DISTANCE;
  }

  return (byte)distance;
}

// The EV3 writes which sensor it wants to read.
void receiveEvent(int numberOfBytes)
{
  if (Wire.available()) {
    byte command = Wire.read();

    if (command >= 1 && command <= 5) {
      requestedSensor = command;
    }
  }

  // Drain any extra bytes.
  while (Wire.available()) {
    Wire.read();
  }
}

// The EV3 requests one byte with the distance.
void requestEvent()
{
  byte sensor = requestedSensor;
  byte value = 0;

  if (sensor >= 1 && sensor <= 5) {
    value = distanceCm[sensor - 1];
  }

  Wire.write(value);
}
