// Five-sensor ultrasonic hub that talks over USB instead of I2C.
//
// The Nano is connected by its own USB cable to the EV3 brick's USB
// port. Under ev3dev it appears as /dev/ttyUSB0 (CH340 chip) or
// /dev/ttyACM0.
//
// Why this rather than the I2C version: the I2C on the EV3 sensor ports
// is not hardware, the brick bit-bangs it in software and it runs at a
// few kHz. At 115200 baud there is bandwidth to spare, and it frees up a
// sensor port as well.
//
// Line format, ASCII terminated with \n:
//
//   U d1 d2 d3 d4 d5 mask frame checksum
//
//   d1..d5    distance from each sensor, in cm
//   mask      bits 0..4, one per sensor: 1 = valid measurement
//   frame     counter of complete sweeps, 0..255
//   checksum  XOR of the seven preceding numbers
//
// A line is printed after EVERY sensor, not after every sweep, so the
// EV3 always has the freshest reading available. That works out to about
// 110 lines per second.
//
// OUT_OF_RANGE_DISTANCE is a sentinel, not a distance. The validity bit
// is what tells a real 125 cm reading apart from a missing echo, and the
// EV3 side depends on that distinction: fed as a distance, one dropout
// looks like an 80 cm jump and slams the steering to full lock.

#define NUM_SENSORS 5
#define MAX_DISTANCE_CM 128
#define OUT_OF_RANGE_DISTANCE 125
#define BAUD 115200

#define ECHO_TIMEOUT_US ((MAX_DISTANCE_CM * 58UL) + 500UL)
#define SENSOR_PERIOD_US 9000UL

// Same wiring as the I2C versions.
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

    // Minimum spacing between triggers, so an echo from one sensor is
    // not still in the air when the next one fires.
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
