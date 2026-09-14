# Ports and Components

## Vehicle

| Parameter | Value |
|:---|---:|
| Mass | **861 g** |
| Dimensions | 24 × 23 × 18 cm |
| Wheel diameter | 56.0 mm |
| Wheel circumference | 175.93 mm |
| Linear travel per motor degree | 0.4887 mm |

See [`docs/Control_Model.md`](../docs/Control_Model.md) for what these
numbers imply about traction, acceleration and steering geometry.

> [!NOTE]
> Every port assignment below was read off the robot with
> `python3 check_hw.py puertos`, which prints what ev3dev actually
> detects on each port. If the wiring changes, re-run that command rather
> than editing this file from memory.

## Motor ports

| Port | Device | Driver reported by ev3dev |
|:---|:---|:---|
| **A** | **Steering** motor | `lego-ev3-m-motor` |
| **B** | **Drive** motor | `lego-ev3-m-motor` |
| **C** | Free | — |
| **D** | Power feed for the Arduino Nano | driven as `dc-motor` |

Both motors are **medium** motors. Port D is not driving a motor: it is
used as a current source for the Nano, held at 100 % duty cycle so the
output is continuous rather than switched. Below 100 % the EV3 output is
a square wave, which a voltage regulator handles badly.

## Sensor ports

| Port | Device | How ev3dev sees it |
|:---|:---|:---|
| **1** | Free | — |
| **2** | mindsensors AbsoluteIMU (gyroscope) | `ms-absolute-imu` on `ev3-ports:in2:i2c17` |
| **3** | HuskyLens camera, via the OFDL UART adapter | `ev3-uart-84` |
| **4** | Free | — |

## USB

| Connection | Device | Appears as |
|:---|:---|:---|
| Brick USB port | Arduino Nano, five ultrasonic sensors | `/dev/ttyUSB0` |

The Nano used to sit on sensor port 4 over I²C. It was moved to USB
because the I²C on the EV3 sensor ports is not hardware: the brick
bit-bangs it in software and it runs at a few kHz. Over USB at 115200
baud there is bandwidth to spare, and it frees a sensor port.

## Electronics

* 1 LEGO EV3 Brick
* 1 Arduino Nano — reads the five ultrasonic sensors and streams them
  over USB
* 5 HC-SR04 ultrasonic sensors
* 1 HuskyLens camera with the OFDL adapter. The adapter carries its own
  microcontroller, which translates the camera's output into the LEGO
  UART protocol; it is not programmed by the team
* 1 custom PCB for sensor routing and power distribution
* 1 5 V voltage converter
* 2 LEGO EV3 medium motors
* Dupont jumper wires and LEGO EV3 cables

## Mechanical

* LEGO EV3 parts
* 3D-printed ultrasonic sensor mounts:
  * 2 mounts holding 4 sensors each
  * 1 mount holding a single sensor

## Ultrasonic sensor pins on the Nano

Sensor numbering matches the order they appear in the serial frame.

| Sensor | Trig | Echo | Position on the robot |
|:---:|:---:|:---:|:---|
| 1 | 11 | 12 | Left, 90 degrees |
| 2 | 9 | 10 | Left, 25 degrees |
| 3 | 7 | 8 | Front |
| 4 | 5 | 6 | Right, 25 degrees |
| 5 | 3 | 4 | Right, 90 degrees |

The mapping between frame index and physical position was measured with
`python3 check_hw.py mapear`, which covers one sensor at a time and
reports which index changes. It is recorded in `Src/ev3dev/wro/config.py`
as `IDX_IZQ`, `IDX_FRONTAL` and `IDX_DER`.
