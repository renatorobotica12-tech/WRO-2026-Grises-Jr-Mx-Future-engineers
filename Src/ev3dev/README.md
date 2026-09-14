# ev3dev control software

Python control software for the competition robot, running on the LEGO
EV3 brick under [ev3dev](https://www.ev3dev.org/). This is a parallel
path to the EV3-G project in `Src/WRO 26.ev3`, not a replacement for it.

## Why ev3dev rather than EV3-G

Writing the control loop as code instead of blocks buys three things
that mattered in practice:

- **The control maths is written literally.** In EV3-G the range mapping
  and the dead band had to be approximated with the blocks available
  (see [`OPEN_ARD_EQUIVALENCIA.md`](../../docs/OPEN_ARD_EQUIVALENCIA.md)).
  Here each piece is written as it is meant to be.
- **The Nano can be read over USB** instead of through the EV3's sensor
  port I2C, which is bit-banged in software and runs at a few kHz.
- **Every tuning value can carry its reasoning.** `wro/config.py` records
  not just what each number is but how it was measured, which is what
  makes it safe for someone else to change it.

## Wiring

Confirmed on the robot with `check_hw.py puertos`:

| Port | Device | How ev3dev sees it |
|---|---|---|
| Sensor 2 | mindsensors AbsoluteIMU | `ms-absolute-imu` on `ev3-ports:in2:i2c17` |
| Sensor 3 | HuskyLens via the OFDL adapter | `ev3-uart-84` |
| Brick USB | Arduino Nano, five ultrasonic sensors | `/dev/ttyUSB0` |
| Motor A | steering | `lego-ev3-m-motor` |
| Motor B | drive | `lego-ev3-m-motor` |
| Motor D | power feed for the Nano | driven as `dc-motor` |

Sensor ports 1 and 4 and motor port C are free.

Both motors are **medium** motors. That is why `robot.py` uses the
generic `Motor` class and not `LargeMotor` or `MediumMotor`: those two
filter by `driver_name`, and `LargeMotor` throws on a medium motor.
Nothing in that file depends on motor size.

### The Nano over USB

The Nano runs
[`ultrasonic_hub_serial.ino`](../arduino_nano/ultrasonic_hub_serial.ino)
and connects by its own USB cable to the brick's USB port. The ultrasonic
wiring is unchanged: same trig and echo pins.

It sends ASCII lines at 115200 baud:

```
U d1 d2 d3 d4 d5 mask frame checksum
```

One line after **every** sensor, not after every sweep, so the EV3 always
has the freshest possible reading. That is about 110 lines per second.
The EV3 discards the stale ones and keeps the most recent complete line.

**The validity mask matters more than it looks.** When a sensor gets no
echo the firmware sends 125 and clears that sensor's bit. 125 is a
sentinel, not a distance. Fed straight into the steering error, one
dropout looks like an 80 cm jump and slams the steering to full lock.
Measured with `check_hw.py lazo`: the error went from +5 to -82 and back
to +31 in under a second, with the robot standing still. `ultrasonics.py`
filters on that bit, holding the last good reading through short
dropouts.

### The HuskyLens

The OFDL adapter does not expose the camera over I2C: it carries an
Arduino Pro Mini that translates the data into the **LEGO UART
protocol**. To the EV3 it is an ordinary LEGO sensor, so **ev3dev detects
it automatically** — no port mode to force, no driver to install.

**The value ordering does not match the adapter's own README.** That
document lists six values as `State, ID, X, Y, W, H`. Measured on the
robot there are **eight** s32 values, in a different order:

```
0 X   1 Y   2 W   3 H   4 ID   5 State   6 and 7 always 0
```

This was confirmed by watching index 5: it alternates between 1 and 7,
exactly the codes for "object detected" and "sees none", and when it
reads 7 all the others drop to zero.

`husky.py` reads `bin_data` rather than eight separate `value(i)` calls.
That is one atomic 32-byte read, so data from two frames can never be
mixed, and it takes 5 ms instead of 49 ms. At 49 ms the camera alone
would hold the control loop down to 20 Hz.

Adapter state codes:

| Code | Meaning |
|---:|---|
| 9 | adapter connected but no HuskyLens attached |
| 8 | connected, no objects learned |
| 7 | connected with learned objects, seeing none |
| 1 | an object is detected |
| 0 | port disconnected or data lost |

`obs_ard.py` prints this state at start-up, before calibrating.

## Layout

Only three files are ever run. `wro/` is a library: the programs import
it, but **nothing inside it is executed directly**.

```
Src/ev3dev/
  check_hw.py        RUN  diagnostics; the first thing to use
  open_ard.py        RUN  open challenge, three laps
  obs_ard.py         RUN  obstacle challenge, three laps

  wro/               nothing here is run directly
    config.py        EDIT THIS: ports, wiring and gains
    robot.py         drive train and steering
    imu.py           AbsoluteIMU, angle integration, corner counting
    ultrasonics.py   the Nano, over USB or I2C
    husky.py         HuskyLens through the OFDL adapter
    ports.py         sensor port I2C modes
    power.py         powering the Nano from a motor port
    i2c.py           raw I2C access
    util.py          numeric helpers
```

Of those three, `check_hw.py` only moves the robot in the `topes`,
`motores` and `volante` commands; everything else just reads and prints.
It is the tool used to fill in `wro/config.py`.

## Installation

On the brick, with ev3dev already running:

```bash
sudo pip3 install pyserial
```

`smbus2` is only needed if the Nano is left on I2C (`ARD_BACKEND = 'i2c'`).

Copy the folder to the brick so it ends up as `~/ev3dev/check_hw.py` and
`~/ev3dev/wro/config.py`:

```bash
scp -r ev3dev robot@ev3dev.local:~/ev3dev
```

```bash
chmod +x ~/ev3dev/*.py
```

The files must keep **LF** line endings. If running them gives
`bad interpreter`, that is the cause — the repository's `.gitattributes`
enforces this for anyone cloning on Windows.

If opening the serial port gives a permission error:

```bash
sudo usermod -a -G dialout robot
```

## Before the first run

Several values can only be measured on the robot. `check_hw.py` settles
them one at a time.

```bash
python3 check_hw.py puertos
```

Lists ports, drivers, I2C buses, serial ports and motors. Confirms the
AbsoluteIMU appears as `ms-absolute-imu`, the HuskyLens as a UART sensor,
and that `/dev/ttyUSB0` exists.

```bash
python3 check_hw.py mapear
```

Works out which frame index is which sensor: takes a baseline with
everything clear, then asks for one sensor to be covered at a time.
Prints `IDX_IZQ`, `IDX_FRONTAL` and `IDX_DER` ready to paste. Hold your
hand about 10 cm away, not against the sensor: too close gives no echo
at all and the firmware returns 125, which confuses the measurement.

```bash
python3 check_hw.py husky
```

Prints the driver, the mode list and the live values. Settles which mode
to use, what range X and Y arrive in, and **which ID belongs to which
colour**. That last one has to be measured: a swapped colour ID produces
exactly the same symptom as reversed target signs, and gets "fixed" the
same wrong way.

```bash
python3 check_hw.py escala
```

Computes `IMU_ESCALA` by integrating all three axes while the robot is
turned through a known angle. The magnitude is already known without
moving anything: the driver reports `units = d/s` and `decimals = 1`, so
the raw integer is ten times the value, giving exactly `0.1`. What this
command really settles is **the axis and the sign**.

```bash
python3 check_hw.py topes
```

Measures the steering travel stop to stop, and prints the
`VOLANTE_LIMITE` that follows from it. Lift the robot first.

```bash
python3 check_hw.py lazo
```

Runs the complete control loop with the motors off. This is the dress
rehearsal: it shows the real loop rate and whether the signs are
consistent.

## Running

```bash
python3 open_ard.py
```

```bash
python3 obs_ard.py
```

Both centre the steering against the stops, calibrate the gyroscope with
the robot still, print the values actually in use, wait for the centre
button, run three laps and stop. The back button stops everything at any
time.

If a program is killed partway and leaves motors running or port D
powered:

```bash
python3 check_hw.py parar
```

## Design decisions worth knowing

**Dropout filtering on the ultrasonic sensors.** A sensor with no echo
keeps its last good reading for `ARD_RETENCION` seconds before being
treated as "no wall nearby". Without this, one flicker sends the steering
to full lock.

**Hold-over on the camera.** The same idea applied to the HuskyLens.
Without it, every one-frame dropout handed control back to wall
following, which at that instant saw a large error and went to full lock:
measured at +1.9 degrees to +50.6 and back inside 300 ms, with the block
in view the whole time.

**Picking which block to avoid.** The adapter returns only one bounding
box per read, and with two blocks in view it switches between them. The
robot latches onto one and only yields control to another that looks
clearly **wider**, meaning closer. Width is the only proximity
information available, and the pillars are identical.

**Discarding false corners.** While avoiding a block the steering goes to
full lock and the robot genuinely turns. The gyroscope cannot tell that
from a track corner and would count it. Measured on track: two corners
1.1 seconds apart where the real ones were arriving every 6. Corners
closer together than `ESQUINA_INTERVALO_MINIMO` are discarded.

**The steering limit comes from the free travel.** Pushed at full power
the mechanism gives 153 degrees; at minimum power it gives 119. The 34
degrees of difference are the mechanism flexing against the stops, not
usable steering. Taking the limit from the forced travel makes the
steering fight the stops on every correction.

**Velocity mode, not raw power.** The drive motor is commanded as a
percentage of maximum speed and the EV3 regulates using the encoder, so a
wheel slowed by a track imperfection gets more power automatically. Raw
duty cycle is open loop and simply stalls.

## Still to verify on track

- Tune `VOLANTE_KP` and `HUSKY_TARGET_*` at competition speed.
- Confirm `HUSKY_INVERTIR_X` after any lens change. It raises no error
  when wrong; it just makes the robot avoid on the wrong side.
- Watch the per-sensor substitution counts printed at the end of each
  run. A sensor substituting a quarter of the time is a hardware fault
  that no amount of gain tuning compensates for.
