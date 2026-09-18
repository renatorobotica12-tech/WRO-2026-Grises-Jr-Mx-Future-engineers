"""Robot configuration: ports, wiring and gains.

Everything that needs adjusting at the track should live in this file.

Most values here are measured rather than chosen. Where that is the case
the comment says how it was measured and what the number means, because
a tuning value with no recorded reasoning is one nobody dares change.
"""


# Underscored so that `from wro.config import *` never exports it, and
# so it is obvious that nothing here is a tuning value.
import math as _math

# --------------------------------------------------------------------
# Ports
# --------------------------------------------------------------------

PUERTO_IMU = 'ev3-ports:in2'        # mindsensors AbsoluteIMU
PUERTO_HUSKY = 'ev3-ports:in3'      # HuskyLens via the OFDL adapter
PUERTO_ARD = 'ev3-ports:in4'        # only if the Nano runs over I2C

# Confirmed on the robot: BOTH motors are medium ones
# (lego-ev3-m-motor), and there is nothing on C or D.
PUERTO_TRACCION = 'outB'            # medium motor
PUERTO_VOLANTE = 'outA'             # medium motor

# --------------------------------------------------------------------
# Arduino Nano ultrasonic hub
# --------------------------------------------------------------------

# 'serial' -> ultrasonic_hub_serial firmware, Nano on the brick's USB port
# 'i2c'    -> ultrasonic_hub_packet firmware, Nano on a sensor port
ARD_BACKEND = 'serial'

ARD_PUERTO_SERIE = None             # None = auto-detect /dev/ttyUSB* or ttyACM*
ARD_BAUDIOS = 115200
ARD_ESPERA_ARRANQUE = 2.0           # opening the port resets the Nano

# Powering the Nano from a motor port, driven as a DC motor. Data still
# travels over USB; this is current only.
# Set to None if the Nano is powered over USB alone.
#
# The duty cycle MUST be 100: below that the EV3 output is a square wave
# rather than continuous, and the Nano's regulator would struggle.
ARD_ALIMENTACION_PUERTO = 'outD'
ARD_ALIMENTACION_DUTY = 100
ARD_ALIMENTACION_ESPERA = 1.5       # seconds before opening the serial port

ARD_DIRECCION = 0x08                # only for ARD_BACKEND = 'i2c'
ARD_FIRMWARE = 'packet'             # 'packet' or 'byte'

# Zero-based indices within the frame.
# Verified on the robot with `check_hw.py mapear`, covering one sensor at
# a time.
IDX_IZQ = (0, 1)                    # left 90 and left 25
IDX_FRONTAL = 2
IDX_DER = (3, 4)                    # right 25 and right 90

ARD_FUERA_DE_RANGO = 125            # the firmware's out-of-range sentinel

# --------------------------------------------------------------------
# Distance filtering
# --------------------------------------------------------------------
#
# When an ultrasonic sensor gets no echo, the firmware returns 125 and
# clears its validity bit. 125 is not a distance, it is a sentinel. Added
# straight into the error, a single sensor dropout makes the error jump
# by 80 cm and the steering slams to full lock. Measured with
# `check_hw.py lazo`: the error went from +5 to -82 and back to +31 in
# under a second, with the robot standing still.
#
# With the filter, a sensor that loses its echo keeps its last good
# reading for ARD_RETENCION seconds. If it is still silent after that,
# it is taken to mean "no wall nearby" and ARD_DISTANCIA_MAXIMA is used.
ARD_FILTRAR = True

# Useful distance ceiling, in cm. Beyond this a reading contributes
# nothing to staying centred between the walls and only adds noise to
# the error. The Future Engineers corridor is 1 m wide; the sensors at
# 25 degrees see somewhat further than the perpendicular ones, hence the
# margin.
ARD_DISTANCIA_MAXIMA = 100

# How long a sensor's last good reading is held when it loses its echo.
# At 44 Hz this is about 22 control loops.
ARD_RETENCION = 0.5

# Rolling median per sensor, to kill isolated spikes that get through
# with their validity bit set. 1 disables it; 3 is enough and adds no
# noticeable lag.
ARD_MEDIANA = 3

# --------------------------------------------------------------------
# IMU
# --------------------------------------------------------------------

# 'driver' -> lego-sensor with the ms-absolute-imu driver (recommended)
# 'raw'    -> direct I2C reads of the gyro registers
IMU_BACKEND = 'driver'

IMU_DIRECCION = 0x11                # 0x22 as 8-bit = 0x11 as 7-bit
IMU_DRIVER = 'ms-absolute-imu'
IMU_MODO = 'GYRO'
IMU_EJE = 2                         # 0=X, 1=Y, 2=Z

# Factor converting the raw reading into degrees per second.
#
# The ms-absolute-imu driver in GYRO mode reports units = d/s and
# decimals = 1: the raw integer comes multiplied by ten. That gives
# exactly 0.1.
#
# Confirmed by measurement: `check_hw.py escala` over one full turn gave
# 0.09795, within 2 %. The exact 0.1 is kept rather than the measured
# value, because 0.1 is exact by construction while the measurement
# carries the error of turning the robot by hand. What the test really
# settled was the axis and the sign.
#
# POSITIVE sign confirmed: turning right, Z accumulates positive.
IMU_ESCALA = 0.1

IMU_MUESTRAS_CALIBRACION = 600      # samples averaged for the zero offset
IMU_ZONA_MUERTA = 0.3               # deg/s below which the robot counts as still

# --------------------------------------------------------------------
# HuskyLens
# --------------------------------------------------------------------

# Confirmed on the robot: ev3dev detects the adapter as `ev3-uart-84`
# and its modes do carry proper names, not MODE0/MODE1.
#   'Data-EV3HSK' -> the bounding box data
#   'Time-EV3HSK' -> another adapter mode, unused here
HUSKY_MODO = 'Data-EV3HSK'

# The real ordering of the eight values, measured on the robot. It is NOT
# the one the adapter's README gives (State, ID, X, Y, W, H): State is at
# index 5, and when nothing is detected every other value drops to zero.
# Indices 6 and 7 always read 0 in this mode.
HUSKY_IDX_X = 0
HUSKY_IDX_Y = 1
HUSKY_IDX_W = 2
HUSKY_IDX_H = 3
HUSKY_IDX_ID = 4
HUSKY_IDX_STATE = 5

# HuskyLens resolution. Subtracted to put the origin at the centre of the
# image, so X runs from -160 on the left to +160 on the right.
HUSKY_CENTRO_X = 160
HUSKY_CENTRO_Y = 120

# Axis inversion, for when the lens delivers the image the other way up.
#
# Correcting it here rather than in the targets is deliberate: inverting
# the axis leaves everything downstream -- targets, clamps, steering sign
# -- meaning exactly what it did before, so swapping a lens does not
# force a retune of the rest.
#
# X is the only one that affects behaviour: it is what angulo_esquive()
# uses. With X inverted the wrong way for how the lens is fitted, the
# robot avoids every block on the wrong side.
#
# Y takes part in no decision today; it is inverted for consistency, so
# that the (X, Y) pair genuinely describes the image.
#
# Verified with `check_hw.py husky`: with the block to the LEFT of the
# camera, X must come out NEGATIVE.
#
# With a 125-degree lens both had to be True, confirmed by measurement:
# left -140, centre -2, right +81. With the original lens the image is
# not rotated, so they go back to False. IF THE LENS IS CHANGED AGAIN,
# measure this again: it is the first thing to break and it raises no
# error at all, it just makes the robot avoid on the wrong side.
HUSKY_INVERTIR_X = False
HUSKY_INVERTIR_Y = False

# IDs learned by the HuskyLens in colour recognition mode.
#
# Measured by holding each block in front and reading the ID, not
# deduced: red is 1 and green is 2. They were swapped for a while, and
# the robot behaved identically because the targets were swapped too;
# what actually broke was that adjusting HUSKY_TARGET_ROJO was really
# adjusting the green one. If the colours are ever re-learned on the
# camera, measure this again with `check_hw.py husky`.
HUSKY_ID_ROJO = 1
HUSKY_ID_VERDE = 2

# THIS IS THE KNOB FOR TUNING HOW THE PILLARS ARE AVOIDED.
#
# It is the position, in pixels, where the robot tries to KEEP the block
# within the image while driving around it. The steering corrects until
# the block arrives there:
#
#   -160  left edge of the image
#      0  centre
#   +160  right edge
#
# If the block has to end up on the LEFT of the image, that means the
# robot is pointing to the right of it, so it passes on the RIGHT. This
# sounds backwards the first time: it is because the camera looks where
# the robot is going, not at the block.
#
#   target further from centre  ->  wider detour, passes further away
#   target closer to centre     ->  tighter squeeze past it
#   target 0                    ->  aims straight at the block and
#                                   drives into it
#
# They are per colour so one colour's detour can be opened up more than
# the other's.
#
# Which colour takes which sign was settled by testing on track, not by
# reasoning: the first reasoned version passed them on the wrong sides.
#
# WATCH OUT: swapped colour IDs produce exactly the same symptom as
# reversed signs, and get "fixed" the same way. `check_hw.py husky` with
# one block of each colour in front is what actually settles which ID
# belongs to which.
#
# The real ceiling is +-160: X is computed as raw - HUSKY_CENTRO_X over a
# 320 px image, so the block can never be beyond that. A target outside
# that range is a position the block can never reach, and the steering
# would never straighten out while the block was in view: it would keep
# turning until the pillar left the frame. At 150 the loop still closes.
HUSKY_TARGET_ROJO = -150            # left in frame  -> passes on the right
HUSKY_TARGET_VERDE = +150           # right in frame -> passes on the left

# Per-colour clamp on the steering angle, as a FRACTION of the limit.
#
# The tighter clamp goes with the colour that steers right, so that the
# robot can cut back harder on one side than the other while rounding a
# pillar.
#
# Fractions rather than degrees on purpose: in degrees they would be tied
# to whatever the steering limit happened to be when they were written,
# and would silently clamp to the wrong fraction of the travel the moment
# VOLANTE_LIMITE changed.
HUSKY_LIMITE_ROJO = (-0.75, 1.0)    # the one that gives a positive command
HUSKY_LIMITE_VERDE = (-1.0, 1.0)

# How long the camera's last good command is held, in seconds.
#
# Same pattern as ARD_RETENCION for the ultrasonic sensors, and for the
# same reason: one failed frame does not mean the block is gone.
#
# It solves the dropout problem measured on track: the camera loses the
# block for one or two loops, control goes back to wall following, which
# at that instant sees a large error and sends the steering to full lock.
# Measured: +1.9 degrees to +50.6 and back inside 300 ms, with the block
# in view the whole time.
#
# The size comes from the real loop period, not from guesswork: at the
# 31 Hz measured, each loop is 32 ms, so below that the window expires
# before the next reading and the hold never engages at all.
#
# The history of this number is measured, not assumed:
#
#   0.1  ->  12 % of loops held. Covered the dropouts.
#   0.3  ->  31 % of loops held, and the block switching was UNCHANGED.
#
# The second result taught us something: the adapter does not alternate
# frame by frame, it stays on a different block for longer than any
# reasonable window. Stretching the window never catches up with it, it
# only makes the robot act on stale images: at speed 40, a third of the
# commands with up to 0.3 s of lag.
#
# So the window is back to what it does well, covering dropouts, and the
# block switching is handled by HUSKY_MARGEN_ANCHO, which is the right
# tool for it.
HUSKY_RETENCION = 0.15

# How much wider a new block has to look before it takes control from the
# one already being avoided. 1.0 accepts any; 1.2 demands it look 20 %
# wider.
#
# The bounding box width is the only PROXIMITY information the adapter
# provides: the track pillars are all identical, so the one that looks
# wider is the one that is closer, and the closest is the one that has to
# be avoided. Without this test, with two blocks in view the robot got
# commands for opposite sides on consecutive loops: measured, id=1 asking
# for +50.6 (right) and 300 ms later id=2 asking for -27.2.
#
# This recovers the "widest box wins" rule. The adapter returns only one
# box per read, but comparing across reads gets to the same place.
#
# The 20 % margin is hysteresis: without it, two blocks at similar
# distances would trade control back and forth on measurement noise
# alone.
HUSKY_MARGEN_ANCHO = 1.2

# --------------------------------------------------------------------
# Steering
# --------------------------------------------------------------------

# Motor degrees corresponding to full steering lock.
#
# Measured with `check_hw.py topes` on this robot:
#
#   low stop -88, high stop +65, centre -12
#   forced travel 153 degrees (pushing at 100 %)
#   free travel   119 degrees (at the lowest power)
#
# The 34 degrees of difference are the mechanism flexing against the
# stops, not usable steering. The limit comes from the FREE travel, with
# a 15 % margin so the steering does not hit the stops on every
# correction. Taking it from the forced travel would give 65, and the
# steering would spend the race fighting the stops.
#
# It sat at 30 for a while, only half the travel available, and the
# steering ran out of angle on track. Then at 45, set by eye. The
# measurement above gives 50.6, and that is rounded to a flat 50 here.
#
# The two stops are declared outright, in degrees, one per side:
#
#       -50  <--  0  -->  +50
#     left     centre     right
#
# Zero is straight ahead, and it is a real zero: preparar_volante()
# finds both mechanical stops at startup and takes the midpoint, so the
# command scale is centred on the mechanism rather than on wherever the
# steering happened to be left pointing.
#
# Written as two separate numbers rather than one limit and a pair of
# fractions, which is what this was before. Fractions made capping one
# side an exercise in arithmetic; these say what they mean, in the same
# unit as every other steering figure. To stop the robot cutting hard to
# one side, lower that side's number and leave the other alone.
#
# The clamp is applied in Robot.girar(), the single point that the wall
# following, the corner anticipation and the camera avoidance all pass
# through, so no path can exceed these.
#
# Sign convention, set by VOLANTE_SIGNO: positive turns RIGHT.
# > [!NOTE]
# > Set to 30, deliberately below the 50 the stops allow.
# >
# > The mechanism reaches 50 a side and nothing here stops it; these two
# > numbers are a policy, not a measurement. 30 is 60 % of the available
# > lock, which buys a gentler line through the corners and less scrubbing
# > from the inside front wheel, at the cost of a wider turning circle.
# >
# > This file has been here before: the limit sat at 30 for a while, and
# > the note from that period says the steering "ran out of angle on
# > track". That was a different machine, though. Since then the stops
# > were measured properly and the corner anticipation was added, so the
# > steering now starts its turn 45 cm out instead of waiting for the
# > lateral difference to grow. Less lock, applied earlier, may well beat
# > more lock applied late.
# >
# > What to watch on the next run: the retreat count. If it climbs off
# > zero, the robot is reaching corners it cannot get round at 30, and
# > the choice is to raise these back towards 50 or to start the turn
# > earlier with GIRO_ANTICIPADO_DISTANCIA.
VOLANTE_TOPE_DERECHO = 55.0
VOLANTE_TOPE_IZQUIERDO = -55.0

# The larger of the two, as a single number. Derived, not a knob: the
# two stops above are the authority. It exists because a handful of
# things need one figure for "full lock" regardless of side -- the
# saturation error below, the camera's clamp in husky.py, the travel
# check in preparar_volante().
VOLANTE_LIMITE = max(VOLANTE_TOPE_DERECHO, abs(VOLANTE_TOPE_IZQUIERDO))

# Wall-following gain: steering degrees per unit of raw error. This is
# the main knob for how aggressive the correction is.
#
# The history of this number is worth reading before changing it. It went
# 0.472, 0.555, 1.2, 2, 3.0 and as high as 10. The 10 was chosen while
# the error was being corrupted by a dead ultrasonic sensor that pinned
# it at a constant +62. With all five sensors healthy the real operating
# error is 5 to 9, and a gain of 10 saturated the steering permanently.
# Hence back down to 3, then 1.5, then back to 3 when the speed went up
# to 70: the faster it travels, the less time it has to correct each
# deviation and the more gain it needs for the correction to arrive in
# time.
VOLANTE_KP = 3

# Wall-following gain INSIDE the obstacle challenge.
#
# Kept separate from the one above on purpose. In the open challenge the
# robot only has to stay centred between the walls and can afford to be
# aggressive. In the obstacle challenge, wall following is what happens
# between one block and the next, and a high gain there leaves the robot
# swinging wall to wall just as the camera is about to take over. It
# usually wants to be gentler than the open-challenge gain.
#
# It is a standalone number: lowering it here does not touch open_ard.py.
#
# It only affects the ultrasonic path. Camera avoidance has its own gain,
# which comes out of HUSKY_TARGET_* and the steering limit.
VOLANTE_KP_OBSTACULOS = 3

# The raw error at which the steering reaches full lock. Not a knob: it
# is derived from the two values above and sits here to make the meaning
# of the gain visible.
#
# With KP 3 and a limit of 50.6, the steering saturates at an error of
# 16.9. For a sense of scale: in a 1 m corridor, drifting 10 cm off
# centre already produces an error of about 40, because all four side
# sensors move at once -- two get closer while two get further away. So
# the steering hits full lock at roughly 4 cm off centre, and below that
# it corrects proportionally: there is a real control band, though a
# narrow one.
#
# If the robot starts weaving, lowering the gain comes before lowering
# the speed.
VOLANTE_ERROR_TOPE = VOLANTE_LIMITE / VOLANTE_KP

# Steering direction. Verified on the robot:
#
#   positive command -> the wheels turn RIGHT
#
# and that is the correct sense, because the raw error is
# -(left - right): if the robot drifts towards the left wall, the left
# distances fall, the error comes out POSITIVE, and the steering has to
# go right to move away. It closes.
#
# It also closes for camera avoidance: the green target is positive,
# which drives the block towards the right of the image, which means the
# robot passes on the left of it.
VOLANTE_SIGNO = 1

# Mechanical trim of the centre, in motor degrees. Added to the steering
# destination, so it shifts the zero without touching the limits.
#
# Normally unnecessary, because VOLANTE_AUTOCENTRAR finds the centre
# against the mechanical stops on every start-up. It is here for a
# misalignment the auto-centring cannot see.
VOLANTE_TRIM = 0.0

# Degrees per second at which the steering runs to its commanded angle.
# At 100 the motor would take 0.2 s to go from centre to full lock and
# the robot would always be correcting late. The medium motor reaches
# 1560, so 600 leaves plenty of headroom without abusing the mechanism.
# One of the first values to tune on track.
VOLANTE_VELOCIDAD = 600

# With True, start-up finds both mechanical stops and takes the midpoint
# as zero. That is the right choice here: the measured free travel is 119
# degrees, or +-59.5, and VOLANTE_LIMITE is 50.6. Properly centred, those
# 50.6 fit on both sides. Starting from a crooked zero, the steering
# would hit a stop before reaching the limit on one side and fall short
# on the other -- which on track looks exactly like a badly set
# VOLANTE_TRIM.
VOLANTE_AUTOCENTRAR = True

# Duty cycles used to find the stops, in order. ALL of them are walked,
# lowest to highest, and the final position is the one that counts.
#
# Measured on this robot: at 25 % the steering does not move at all; at
# 40 % it advances 28 degrees and jams halfway; it takes 100 % to
# actually reach the stop. So it is not enough to raise the power only
# when the motor fails to start: it has to be raised every time.
#
# It starts at 40 because 25 moves nothing and would only waste time.
VOLANTE_DUTIES_CENTRADO = (40, 70, 100)

# --------------------------------------------------------------------
# Drive train and race
# --------------------------------------------------------------------

# How the drive train is commanded:
#
#   'velocidad' -> the number is a % of the motor's maximum speed and the
#                  EV3 regulates using the encoder. If a wheel is slowed
#                  by a track imperfection, it raises power on its own
#                  until the commanded speed is recovered.
#   'potencia'  -> the number is the raw duty cycle. Open loop: against
#                  an obstacle the power does not change and the robot
#                  simply stalls.
#
# Changed to 'velocidad' because on track the robot kept bogging down on
# surface imperfections. This is only possible because the motor has an
# encoder.
TRACCION_MODO = 'velocidad'

# What the speed NUMBERS below mean. This is a unit, not a behaviour:
# the drive train is regulated by TRACCION_MODO either way.
#
#   'cm_s'       -> the number IS the ground speed in centimetres per
#                   second. VELOCIDAD = 20 means the robot travels 20 cm
#                   every second. This is the useful one: the value you
#                   write is the speed you get, so a change of 5 is
#                   always the same change on the floor.
#   'porcentaje' -> the number is a percentage of the motor's maximum,
#                   the way this file worked before. 70 means 70 % of
#                   1560 deg/s, which is a different ground speed on
#                   every robot and tells you nothing by itself.
#
# Both are converted to the same motor command in Robot.avanzar(); see
# there for the arithmetic.
VELOCIDAD_UNIDAD = 'porcentaje'

# Reduction between the drive motor and the rear wheel, as
#
#     motor turns / wheel turns
#
# Greater than 1 means geared DOWN: the motor turns more than the wheel,
# which trades speed for torque. 1.0 is direct drive.
#
# This is the one number the cm/s conversion cannot do without, and it
# has never been measured on this robot. Measure it with
#
#     python3 check_hw.py reduccion
#
# which reads the encoder while you turn the rear wheel one full turn by
# hand. Until then it stays at 1.0 and every centimetre figure is only as
# right as that assumption. Nothing else in the code depends on it.
TRACCION_REDUCCION = 1.0

# Diameter of the DRIVEN rear wheel, in millimetres. The black pair.
#
# Not the turquoise front pair: those are steered and undriven, they
# turn at whatever rate the floor dictates, and no arithmetic here
# involves them. See docs/Control_Model.md §1.1.
#
# This number sets the scale of every centimetre figure in this file. If
# the wheels are ever changed, this is the one line to update and the
# speeds keep meaning what they say.
RUEDA_TRASERA_DIAMETRO = 56.0

# Open challenge speed: percent of the motor maximum, 0 to 100.
#
# 70 means 70 % of 1560 deg/s, 5 means 5 %, and the motor holds that
# speed by the encoder rather than just applying that much power.
#
# What each number is on the ground, with the 175.93 mm rear wheel:
#
#     deg/s   = % x 15.6
#     cm/s    = % x 0.762
#
# so 5 % is 3.8 cm/s, 40 % is 30.5 cm/s and 100 % is 76.2 cm/s. Both
# race programs print this at startup for the value actually in use, so
# there is nothing to work out by hand.
#
# Lowered from 70 because the open run was too fast to steer cleanly,
# which is what started this. 40 is about 30 cm/s.
#
# The faster it goes, the less time the steering has to correct each
# deviation. If it starts weaving, the first thing to lower is
# VOLANTE_KP, not the speed.
VELOCIDAD = 40                      # open challenge, % of the motor maximum

# Obstacle challenge speed. DECOUPLED from the one above: it runs slower
# on purpose, because the camera has to see the block, decide which side
# to pass, and fit the whole detour in before reaching it. At the open
# challenge speed the robot arrives on top of the block without having
# finished going around it.
#
# Untouched. The obstacle run works at 40 and is not being retuned.
VELOCIDAD_OBSTACULOS = 40                # obstacle challenge, % of the maximum

# > [!NOTE]
# > The centimetre figures assume direct drive until
# > `check_hw.py reduccion` is run. If the drive train is geared down,
# > the real ground speed is lower than the cm/s shown, by exactly the
# > reduction. The percentages and the motor commands are unaffected
# > either way: only the translation to centimetres depends on it.

ESQUINAS_META = 12                  # three laps
ANGULO_ESQUINA = 87.0               # |angle| threshold for counting a corner

# Minimum time between two corners, in seconds.
#
# A deliberate addition, and one that became necessary as soon as the
# camera started commanding the steering.
#
# The problem, as measured: while avoiding a block the steering goes to
# full lock and the robot genuinely turns. The gyroscope cannot tell that
# turn from a track corner, accumulates its 87 degrees and adds a corner
# that does not exist. In a one-lap run, two corners came out 1.1 seconds
# apart where the real ones were arriving every 6.
#
# In obs_ard.py that is a race-losing fault: each false corner brings the
# target of 12 closer and the robot brakes mid-track believing it has
# already completed three laps.
#
# 1.5 s excludes the measured case with margin and stays well below any
# real spacing: at the highest speed tested, corners arrive every 2 to 3
# seconds.
ESQUINA_INTERVALO_MINIMO = 1.5

# How much further the robot drives after counting corner number 12,
# before braking. During that extra half pass it is still centring
# between the walls with the ultrasonic sensors; it is not driving blind.
#
# 500 ms rather than something shorter, so the robot finishes inside the
# start zone instead of braking the moment it clears the last corner.
MS_EXTRA_AL_FINAL = 500             # open challenge
MS_EXTRA_AL_FINAL_OBS = MS_EXTRA_AL_FINAL

PERIODO_LAZO = 0.02                 # 50 Hz ceiling

# --------------------------------------------------------------------
# Starting the corner early
# --------------------------------------------------------------------

# Lets the forward ultrasonic command the steering, not just the retreat.
#
# Why it is needed: the centring error is the DIFFERENCE between the two
# sides. Coming up on a corner square on, both walls are about equally
# far away, the difference stays near zero, and the proportional term
# has nothing to act on. The steering sits centred until the robot is
# already in the corner. On the first run with the collision guard this
# showed as the robot repeatedly arriving nose-first at 14 cm from a
# wall: the guard was catching a steering failure, not a stray reading.
#
# The front sensor sees that wall from half a metre out. Below the
# distance set here it asks for a turn towards the open side, growing
# from nothing at the threshold to full lock at the wall, and whichever
# of the two commands wants more steering is the one that gets used.
GIRO_ANTICIPADO_ACTIVO = True

# Distance ahead, in centimetres, at which the corner starts.
#
# Too small and the robot still arrives square, which is the fault being
# fixed. Too large and it starts cutting corners in the middle of a
# straight, because a corridor end is visible long before it matters.
#
# 45 cm is a starting point, not a measurement: it is roughly three
# times PRECAUCION_DISTANCIA, so the turn has a good margin to develop
# before the guard would ever fire. Tune it by watching how many
# retreats a run reports — the number should go to zero.
GIRO_ANTICIPADO_DISTANCIA = 45

# --------------------------------------------------------------------
# Front collision guard
# --------------------------------------------------------------------

# The forward-facing ultrasonic finally does something. Until now it was
# read on every frame, because it arrives in the same packet as the
# other four and costs nothing, and then ignored: the wall centring uses
# only the four lateral sensors, so nothing consulted hub.frontal.
#
# What it does now: if something is closer than PRECAUCION_DISTANCIA
# ahead, back off before touching it. Reaching a wall nose-first is the
# one situation the centring controller cannot get out of, because the
# error it works from is the DIFFERENCE between the two sides. Square on
# to a wall that difference is zero, the steering sits centred, and the
# robot drives into it at full speed while the control law reports that
# everything is fine.
PRECAUCION_ACTIVA = True

# Distance ahead, in centimetres, that triggers the retreat.
#
# It reads hub.frontal, which is already filtered: median of the last
# ARD_MEDIANA frames, on top of the dropout hold. A single bad frame
# cannot trigger a retreat, which matters because a spurious one in the
# middle of a lap is worse than the collision it would be avoiding.
PRECAUCION_DISTANCIA = 15

# How far back to go, in turns of the rear WHEEL, not of the motor. The
# conversion uses TRACCION_REDUCCION, so this stays the same distance on
# the ground if the gearing is ever measured or changed.
#
# 0.5 turns of the 56 mm wheel is 8.8 cm of ground. Enough to clear the
# wall and give the steering room to point somewhere useful, without
# reversing so far that it undoes the lap.
PRECAUCION_VUELTAS = 0.5

# Speed of the retreat, as a percentage. Deliberately higher than the
# racing speed: this is a manoeuvre to finish quickly and get back to
# the lap, not something to creep through.
PRECAUCION_VELOCIDAD = 50

# Ceiling on how long one retreat may take, in seconds. If the motor
# stalls against something, the robot must not sit there pushing until
# the run is over.
PRECAUCION_TIEMPO_MAXIMO = 3.0

# Consecutive retreats allowed before the guard switches itself off for
# the rest of the run.
#
# A retreat is supposed to fix the thing that caused it: back away, and
# the distance ahead grows. If it does not grow, backing away again will
# not help either, and the robot is stuck in a loop that costs it the
# run. That is what happened on the first outing: eighteen retreats with
# the distance ahead reading 14 cm throughout.
#
# Something that never clears is not an obstacle. It is the sensor
# seeing part of the robot, or IDX_FRONTAL pointing at a sensor that is
# not the front one, in which case a wall alongside reads 14 cm for the
# whole lap. Neither is fixed by reversing.
#
# So after this many in a row without improvement the guard gives up,
# says so, and lets the lap continue unprotected. An unprotected lap is
# worse than a guarded one, but it is much better than a robot that
# reverses in place until time runs out.
PRECAUCION_MAXIMOS_SEGUIDOS = 3

# Same guard during the obstacle challenge. ON, with a condition.
#
# The obvious problem with a front guard in this run is that the robot
# closes on the blocks on purpose: the camera steers towards one until
# it is near enough to go round it. A guard that simply watched the
# front sensor would read the block, reverse out of the manoeuvre, and
# the camera would drive straight back in. The two would take turns
# undoing each other until the run ended.
#
# So in obs_ard.py the guard only looks while the camera is NOT
# commanding the steering. Going round a block, the thing filling the
# front sensor is that block and the approach is intentional, so the
# guard stays quiet. With no block in view, something close ahead is a
# wall, and that is the failure this exists for: square on to a wall the
# difference between the two sides is zero, the steering sits centred,
# and the controller reports that everything is fine.
#
# The camera's HELD verdict is what gates it, so a one- or two-frame
# dropout in the middle of an avoidance does not open a window for a
# spurious retreat.
PRECAUCION_ACTIVA_OBSTACULOS = True

# Trigger distance for the obstacle run, kept separate from the open
# challenge's.
#
# It can afford to be shorter. The guard here only fires with no block
# in view, so it is not racing the camera for the same space, and a
# shorter distance leaves more room before it ever interrupts. Raise it
# towards PRECAUCION_DISTANCIA if a run shows the robot reaching walls
# it cannot turn out of.
PRECAUCION_DISTANCIA_OBSTACULOS = 12

# Console telemetry for obs_ard.py.
#
# Rate limited on purpose: the loop runs at about 40 Hz, and writing 40
# lines a second over ssh on a Bluetooth link slows down the very loop it
# is trying to measure. At 4 Hz it is still readable and stays out of the
# way.
OBS_TELEMETRIA = True
OBS_TELEMETRIA_HZ = 4

# --------------------------------------------------------------------
# Parking exit
# --------------------------------------------------------------------

# Used only by salida.py, which backs the robot out of a parking bay
# rather than into one. Four phases:
#
#   1. creep forward until the wall ahead is SALIDA_FRENTE_MINIMO away
#   2. pick the side the wall is on: the one reading LESS distance
#   3. steer towards that wall and reverse, which swings the nose out
#   4. counter-steer and drive forward, out of the bay
#
# Phase 3 is the one worth understanding. Reversing with the front
# wheels turned towards the wall pivots the vehicle so the nose swings
# AWAY from it. Steering away and reversing would do the opposite and
# bury the nose deeper into the bay.

# One speed per phase, in VELOCIDAD_UNIDAD. They are three separate
# numbers because the three jobs are not the same job:
#
#   AVANCE    drives into open space with the front sensor aimed at the
#             only thing it can hit, and stops on that sensor.
#   RETROCESO goes blind, for a fixed time, with the wheels over. There
#             is no rear sensor, so nothing would catch a mistake here.
#   SALIDA    drives out of the bay, front sensor watching again.
#
# All three are still slow. There is a wall within centimetres in at
# least two directions for most of this manoeuvre.
#
# > [!NOTE]
# > For converting any of them: deg/s = % x 15.6 and cm/s = % x 0.762,
# > so 0.5 % is 0.38 cm/s, 1 % is 0.76 and 2 % is 1.52. Below about 1 %
# > the drive train may creep in stutters rather than gliding, as the
# > speed controller fights static friction. The program prints all
# > three converted before it runs.
SALIDA_VELOCIDAD_AVANCE = 6
SALIDA_VELOCIDAD_RETROCESO = 8
SALIDA_VELOCIDAD_SALIDA = 3

# The approach is in two stages, and it is the second that keeps the
# wall standing.
#
#   further than SALIDA_FRENTE_LENTO      -> SALIDA_VELOCIDAD_AVANCE
#   between that and SALIDA_FRENTE_MINIMO -> SALIDA_VELOCIDAD_SALIDA
#   at SALIDA_FRENTE_MINIMO               -> stop
#
# Why the middle stage exists. At 40 % the robot covers 30.5 cm/s. One
# pass of the control loop is 20 ms, so it travels 0.6 cm between two
# looks at the sensor; the median of ARD_MEDIANA frames adds a couple of
# frames of lag on top, and the drive train still has to stop. Braking
# from 30 cm/s at a 10 cm threshold leaves very little margin, and the
# thing on the other side of that margin is the wall.
#
# Arriving at the last 25 cm already slowed to 0.4 cm/s removes the
# problem: at that speed a whole loop is a twentieth of a millimetre and
# the overshoot stops mattering.
SALIDA_FRENTE_LENTO = 25

# How close to the wall ahead the approach stops. The pink wall of the
# bay, in practice.
#
# > [!WARNING]
# > 1 cm is below what the sensor can measure. An HC-SR04 does not
# > resolve much under 2 cm: the echo returns while the transducer is
# > still ringing from its own pulse, and the firmware reports 125, the
# > out-of-range sentinel, exactly as if nothing were there.
# >
# > This is already written down elsewhere in the project. The mapping
# > procedure in the ev3dev README tells you to hold a hand at about
# > 10 cm and not against the sensor, for this reason.
# >
# > What that does to an approach aimed at 1 cm: the reading is lost at
# > around 2, ARD_RETENCION holds the last good value for half a second,
# > and then the filter concludes there is no wall nearby and
# > substitutes ARD_DISTANCIA_MAXIMA. The robot would read 100 cm with
# > its nose against the wall and keep pushing.
# >
# > So the threshold below is kept at what was asked for, and
# > SALIDA_FRENTE_SALTO catches the failure instead. Expect the approach
# > to end on the lost echo rather than on the distance: that is the
# > sensor working as designed, not a fault.
SALIDA_FRENTE_MINIMO = 3.0

# How far ahead counts as CLEAR, ending the reverse.
#
# The reverse has no target angle and no target distance: it backs
# straight out until the front sensor stops seeing the wall, and this is
# Lost-echo guard for the approach, both in centimetres.
#
# Once the front sensor has read closer than SALIDA_FRENTE_CERCA, a
# reading that then jumps up by more than SALIDA_FRENTE_SALTO is not the
# wall retreating. Walls do not do that. It is the echo being lost at
# point blank range and the filter substituting its no-wall value, and
# the only safe response is to stop, because the wall is closer than it
# has ever been rather than further.
SALIDA_FRENTE_CERCA = 15
SALIDA_FRENTE_SALTO = 20

# Which way the steering goes for the reverse. 'derecha' or 'izquierda'.
#
# With SALIDA_LADO_AUTOMATICO off this is the side, every time. With it
# on it is the fallback: the side used when the two lateral readings are
# too close to tell apart, which is also what happens if the sensors are
# not answering.
SALIDA_LADO = 'derecha'

# Read the exit side off the lateral sensors instead of taking it from
# the line above.
#
# The robot leaves towards whichever side has more room. A bay against
# the left wall has to be left to the right and the other way round, and
# getting it backwards means reversing into the wall the manoeuvre was
# supposed to swing away from.
#
# This reverses an earlier decision, and the reasoning it replaces is
# worth keeping in view: the side was fixed on purpose so the manoeuvre
# would be identical every run, with one line to change for a mirrored
# bay. That buys repeatability, and it is the right trade when the bay
# is always on the same hand. It is the wrong one when the robot has to
# start from wherever it is put.
#
# The decision is taken ONCE, before the first cycle, and holds for the
# whole manoeuvre. It is not re-read each time round. A multi-point turn
# works by every pass adding rotation to the one before it, so a side
# that changed halfway would spend the second half undoing the first.
SALIDA_LADO_AUTOMATICO = False

# How much further one side has to read, in centimetres, before it is
# preferred over the other.
#
# Below this the two sides are called a tie and SALIDA_LADO decides.
# Without a margin the choice would come down to a centimetre of
# ultrasonic noise, and a robot parked square in a symmetric bay would
# pick its side by luck.
SALIDA_LADO_MARGEN_CM = 5.0

# Seconds of readings averaged before deciding.
#
# One frame is not a measurement. The lateral sensors are the pair this
# program does not otherwise trust -- aimed obliquely at a wall they
# lose the echo entirely -- so the decision is taken off an average
# rather than off whatever a single frame happened to return.
SALIDA_LADO_MUESTREO = 0.4

# Full lock for the parking manoeuvre, in degrees per side.
#
# Separate from VOLANTE_TOPE_* on purpose, and it is the phases of this
# manoeuvre alone that use it -- through the `limite` argument of
# Robot.girar(). The race programs never pass that argument and keep
# turning within VOLANTE_TOPE_*, including the obstacle run this
# programme chains into once the robot is out.
#
# Why they want different numbers: a multi-point turn out of a bay is
# rotation with nowhere to go, and every degree of lock is another
# degree of rotation per pass. Wall following at speed wants the
# opposite -- a steering that answers proportionally and does not sit
# against its stops.
#
# > [!IMPORTANT]
# > 75 is past where the steering moves freely. Measured on this robot:
# > 52 degrees of free travel in total, about 26 a side, against 159
# > degrees forced at full power, about 79 a side. The 53 degrees
# > between the two are the mechanism flexing against its stops, not
# > steering.
# >
# > So this asks for lock that only arrives by pushing, and the motor
# > sits stalled at the stop for the 0.6 s each phase waits after
# > commanding it. Twice a cycle, cycle after cycle. That is heat in a
# > medium motor, and it is the reason the racing limit is worked out
# > from the FREE travel instead.
# >
# > It is a deliberate trade for a manoeuvre measured in seconds. If the
# > steering starts missing its angles or the motor comes back hot,
# > this is the first number to bring down.
SALIDA_VOLANTE_TOPE = 75.0


# --------------------------------------------------------------------
# entrada.py: getting INTO the bay
# --------------------------------------------------------------------
#
# Read by entrada.py alone. The exit programmes never look at any of it,
# and entrada.py borrows exactly one number from theirs -- the steering
# stop above, because full lock is full lock whichever way the robot is
# going through the gap.

# Which side of the robot the bay is on: 'derecha' or 'izquierda'.
#
# This one means what it says. It is NOT the crossed steering name that
# SALIDA_LADO carries: the entry has no reverse-then-forward pairing
# whose lock has to be read backwards.
ENTRADA_LADO = 'derecha'

# Which parts of the programme run: 'completo', 'buscar' or 'maniobra'.
#
#   'completo' -> A search, B position, C reverse in, D straighten, E centre
#   'buscar'   -> A only. Finds the bay, prints what it measured, stops.
#   'maniobra' -> skips the search. Creeps ENTRADA_ARRANQUE_CM forward
#                 and goes straight into C.
#
# One setting rather than two flags, because two flags have a fourth
# combination that means nothing and would still have to be handled.
#
# What each is for: 'buscar' checks the detection without letting the
# robot reverse on the strength of it. 'maniobra' is for working on the
# park itself -- stand the robot beside the bay by hand and try the
# angles, without driving the length of the wall first every time.
# 'completo' is the race.
ENTRADA_MODO = 'maniobra'

# Creep before the manoeuvre in 'maniobra' mode, in centimetres.
#
# Small on purpose. It is not positioning -- the hands did that -- it
# is a moment of forward motion to take up the backlash in the drive
# train, so the reverse starts from a tight gearbox and the first
# centimetres of the swing are real.
ENTRADA_ARRANQUE_CM = 30.0

# Speed while looking for the bay, percent of the motor maximum.
ENTRADA_VELOCIDAD_BUSQUEDA = 6

# Speed for the manoeuvre itself.
ENTRADA_VELOCIDAD_MANIOBRA = 8

# The jump in the lateral reading, in centimetres, that counts as an
# edge of the bay.
#
# Both edges are the same event in opposite directions: the wall falls
# away at the mouth and comes back at the far end. Too small and every
# lost echo is a bay; too large and a shallow bay is never noticed.
ENTRADA_SALTO_CM = 15.0

# The gap has to measure between these two to be the bay.
#
# Shorter is a doorway, a gap between blocks, or a sensor that missed
# for a moment. Longer is not a bay at all, it is open floor -- the far
# side of the mat, or a corner taken wide.
ENTRADA_LARGO_MINIMO_CM = 20.0
ENTRADA_LARGO_MAXIMO_CM = 80.0

# Ground covered after the far edge before reversing, in centimetres.
#
# The search stops when the SENSORS are level with the far edge, and it
# is the rear axle that has to be there before the reverse starts. This
# closes that gap. It is the number most likely to need a pass on the
# track: too little and the robot clips the near marker on the way in,
# too much and it ends up short of the bay.
ENTRADA_ADELANTO_CM = 5.0

# Heading swung during the reverse-in, in degrees.
#
# The classic parallel park is about 45. Less needs a longer bay;
# more tucks in tighter but asks the counter-steer to undo more, and
# there is a wall at the back while it does.
ENTRADA_ANGULO = 45.0

# How close to parallel counts as parallel, in degrees.
ENTRADA_ANGULO_TOLERANCIA = 5.0

# Encoder ceiling for EACH of the two reversing phases, in centimetres.
#
# > [!IMPORTANT]
# > This is a backstop for a gyro that never reaches its angle, and it
# > is reversing towards the back of a bay with no sensor watching.
# > Keep it to about the length of the bay, never more.
ENTRADA_RECORRIDO_MAXIMO_CM = 40.0

# How far to look for the bay before giving up, in centimetres.
ENTRADA_BUSQUEDA_MAXIMA_CM = 300.0

# Small forward nudge at the end, to sit off the back of the bay.
ENTRADA_CENTRAR_CM = 5.0

# The ID the parking marker is learned as on the HuskyLens.
#
# Defaults to the same one salida.py uses, because it is the same
# physical bay -- seen from outside here and from inside there. Split
# them if the two views end up wanting different learned colours.
#
# Written out rather than pointing at SALIDA_ID_BAHIA: that one is
# defined further down this file, and a forward reference here fails at
# import. Keep the two in step by hand.
ENTRADA_ID_BAHIA = 3

# The camera has to confirm the gap before it counts as the bay.
#
# A gap in a wall is not a parking bay. It is also a doorway, the space
# between two blocks, or a corner taken wide. The lateral pair can say
# that something is missing from the wall; only the camera can say
# WHICH something. With this off, any gap of the right length is taken,
# which is how the first version worked and is not good enough.
ENTRADA_CAMARA_OBLIGATORIA = True

# Narrowest detection, in pixels, that counts as the marker. Same
# reasoning as SALIDA_BAHIA_ANCHO_MINIMO: the ID on its own is not
# evidence under changed lighting.
ENTRADA_CAMARA_ANCHO_MINIMO = 20

# How far back a sighting still counts, in centimetres of travel.
#
# In DISTANCE, not seconds. The robot's speed is a setting, and a
# memory measured in seconds would cover a different length of wall
# every time that setting changed.
ENTRADA_CAMARA_RETENCION_CM = 60.0

# Every FORWARD move stops this far short of whatever is ahead.
#
# Forward is the direction with a sensor, so a forward move that drives
# into something is a move that chose not to look. Phase B runs the
# length of the bay and more, and whatever is parked past it does not
# move out of the way.
ENTRADA_FRENTE_GUARDIA_CM = 15.0

# How many goes at the bay before giving up.
#
# One swing in is rarely enough from a tight bay: it gains angle
# without gaining a place, meets the wall, and needs another. Each go
# starts from where the last left the robot, so they accumulate.
ENTRADA_INTENTOS_MAXIMOS = 5

# Backstop for a robot getting nowhere, in seconds.
ENTRADA_TIEMPO_TOTAL_MAXIMO = 120.0

# Lateral reading, in centimetres, at or below which the robot counts as
# alongside the bay wall rather than still out in the corridor.
ENTRADA_DENTRO_LATERAL_CM = 20.0

# Ground covered pulling forward between attempts, in centimetres, with
# the steering at the counter lock. This is what sets up the next go.
ENTRADA_CORRECCION_CM = 12.0

# What starts the manoeuvre: 'camara' or 'ultrasonico'.
#
#   'camara'      -> drive straight past the bay wall and start the
#                    moment the marker LEAVES the frame
#   'ultrasonico' -> measure a gap between two jumps in the lateral
#                    pair, with the camera confirming it is the bay
#
# 'camara' is the better of the two and it is not close. The ultrasonic
# version answers "is there a gap here", and then needs the camera to
# answer "is this gap the bay", and then needs ENTRADA_ADELANTO_CM to
# turn a gap that was measured behind the robot into a place to start
# reversing from. The camera version answers all three at once: the
# marker leaving the frame IS the robot arriving level with the edge.
#
# What it costs: the trigger is an ABSENCE, and absence is the weaker
# kind of evidence. A marker leaves the frame because the robot reached
# the edge -- or because the light changed, or the angle did. Two guards
# below are what make it usable.
ENTRADA_DISPARO = 'camara'

# How far the marker has to STAY gone before the absence is believed,
# in centimetres of travel.
#
# One frame without it is noise: the marker flickers out for all sorts
# of reasons. This is the same idea as SALIDA_CONFIRMAR_SEGUNDOS in the
# exit programme, in distance rather than seconds so that changing the
# search speed does not quietly change how much wall it covers.
ENTRADA_PERDIDA_CM = 5.0

# --------------------------------------------------------------------
# Phase 4: straightening up, once out
# --------------------------------------------------------------------
#
# The exit is an arc, so the robot arrives in the corridor still turned.
# Phase 4 takes that angle back out: it counter-steers to the stop
# OPPOSITE the one the exit used, drives a little on that lock, centres
# the steering and reverses.
#
# Why the reverse at the end: the counter-steer swings the nose back
# square but carries the robot forward across the corridor while it does
# it. Backing up on a centred wheel returns that ground without undoing
# the rotation, which is the half of the movement worth keeping.
#
# It runs ONCE, after the exit has been confirmed, not inside the cycle.
# The trigger asked for was the moment the exit speed engages; confirmed
# exit is the same signal with the guesswork removed, and it cannot fire
# from a front reading that happened to open up mid-bay.
SALIDA_ENDEREZAR = True

# Ground covered ON THE EXIT LOCK, before anything is straightened.
#
# Phase 3 ends with the wheels hard over and this carries that on: the
# robot keeps arcing the way it came out, now with room to do it in.
# Where the straight stretch below is for putting distance between the
# robot and the bay, this one is still rotation -- the last of the turn,
# taken outside the bay instead of inside it.
#
# Set it to 0 to skip it and go straight to the centred run.
SALIDA_ENDEREZAR_ARCO_CM = 30.0

# Ground covered before the counter-steer, in centimetres, STRAIGHT.
#
# The steering is centred for this stretch. Phase 3 ends with the wheels
# hard over, and carrying that lock into the margin would not be a run
# clear of the bay -- it would be more of the arc the robot has just
# finished, delivered after it is already out. At 3 cm that hardly
# showed; at 20 it is most of a turn.
SALIDA_ENDEREZAR_MARGEN_CM = 0.0

# Ground covered ON the counter-lock. This is the part that does the
# straightening; the rest of the phase sets it up and cleans up after.
SALIDA_ENDEREZAR_AVANCE_CM = 25.0

# Ground given back afterwards, steering centred.
#
# > [!IMPORTANT]
# > Backwards, with no sensor pointing that way. What protects it is the
# > same stall detector phase 2 uses -- wheels that stop turning while
# > the motor is still driving them mean something is there, and the
# > move is cut short. That is a detector, not a sensor: it notices the
# > contact, it does not avoid it. Keep this short.
SALIDA_ENDEREZAR_RETROCESO_CM = 25.0

# Speed for all three moves of the phase, percent of the motor maximum.
# Slow on purpose: every one of them is short, and the starting
# transient is a bigger share of a short move than of a long one.
SALIDA_ENDEREZAR_VELOCIDAD = 10

# How long the reverse lasts, in seconds. Not a distance and not an
# angle: the phase is purely timed.
#
# Eight seconds at SALIDA_VELOCIDAD_RETROCESO covers 12.2 cm, which is
# about 245 degrees of motor: a proper reposition rather than a nudge.
#
# The length also settles the starting transient. The motor spends the
# first fraction of a second coming up to speed and taking up the
# backlash in the drive train; at 0.10 s that transient was the whole
# movement, and at 8 s it is under a percent of it.
#
# What the alternatives look like at this speed:
#
#        1 s -> 1.5 cm      10 s -> 15.2 cm
#        8 s -> 12.2 cm     30 s -> 45.7 cm
#
# The program prints the figure for whatever is set here before it runs,
# and reads the encoder afterwards to report how far the robot actually
# went, so this never has to be taken on trust.
# How far the reverse goes, in centimetres of ground.
#
# A distance, not a duration, and the change matters here more than it
# usually would. Timed, the phase delivered what the drive train felt
# like giving: the encoder twice reported 57 % of the commanded rotation
# when reversing with the front wheels held over, so 8.5 s of a nominal
# 13 cm arrived as about 7.4. Driving to an encoder target removes that
# whole question -- it stops when the wheels have turned 6 cm worth,
# whatever the friction did on the way.
SALIDA_RETROCESO_CM = 5.5

# Ceiling on that reverse, in seconds. Derived: the time it should take
# at SALIDA_VELOCIDAD_RETROCESO, times a margin, so a wheel that slips
# the whole way cannot stall the run. The stall detector below is the
# faster of the two and normally acts first.
SALIDA_RETROCESO_MARGEN_TIEMPO = 3.0

# Ceiling on the way out, in wheel turns. NOT a target: phase 3 drives
# until the front sensor opens up, and this only stops it circling.
#
# Driving forward at full lock is driving in a circle. In a bay too open
# to touch a wall and too closed to read as clear, nothing else would
# ever end the phase. 3 turns is about 53 cm, comfortably more than the
# arc needed to swing a nose out of a bay, so reaching it means the turn
# is not working rather than that it needs longer.
SALIDA_SALIR_VUELTAS = 3.0

# Minimum the exit must travel before it may call itself clear, in
# wheel turns. 0.5 turns is about 8.8 cm.
#
# Without it the phase could finish having moved nothing at all, and on
# track it did, in all five cycles of a run: "parado por libre: 0.00
# vueltas", every time.
#
# The reason is that phase 3 starts immediately after an approach that
# ended on a lost echo, with the nose against the wall -- and a lost
# echo is what the filter converts into "no wall nearby" once
# ARD_RETENCION runs out. The first front reading of the phase was 100
# with the robot touching something. Driving a little first makes the
# reading real, because by then the sensor is getting echoes back from
# wherever the robot actually is.
SALIDA_SALIR_MINIMO = 0.5

# Phase 1 ceiling, in wheel turns. If the wall ahead never comes within
# SALIDA_FRENTE_MINIMO, the bay is not where the robot thinks it is and
# creeping forward for ever is the wrong answer.
SALIDA_AVANCE_MAXIMO = 2.0

# Seconds a phase may take before it gives up. DERIVED, not chosen.
#
# It has to be derived, because at these speeds a fixed number is
# guaranteed to be wrong. An earlier version of this file had a flat 12
# seconds next to a speed of 0.4 cm/s, where the longest phase needs 92:
# every phase would have timed out before the robot had gone anywhere,
# and the manoeuvre could never have completed once.
#
# So it is computed from the speed and the longest phase, with the
# factor below as headroom. It uses the SLOWEST of the phase speeds, so
# it is a ceiling for all of them.
#
# The 1560 is the medium motor's maximum in deg/s. It is hardcoded here
# rather than read from the motor because config.py describes the robot
# without talking to it; being a few percent out only shifts a backstop.
SALIDA_MARGEN_TIEMPO = 2.0

_SALIDA_CIRCUNFERENCIA_CM = _math.pi * RUEDA_TRASERA_DIAMETRO / 10.0
_SALIDA_CM_S = (min(abs(SALIDA_VELOCIDAD_AVANCE),
                    abs(SALIDA_VELOCIDAD_SALIDA)) / 100.0 * 1560.0 / 360.0
                * _SALIDA_CIRCUNFERENCIA_CM)
_SALIDA_VUELTAS_MAXIMAS = max(SALIDA_AVANCE_MAXIMO, SALIDA_SALIR_VUELTAS)

SALIDA_TIEMPO_MAXIMO = (SALIDA_MARGEN_TIEMPO
                        * _SALIDA_VUELTAS_MAXIMAS
                        * _SALIDA_CIRCUNFERENCIA_CM
                        / _SALIDA_CM_S)

# How many times the whole cycle runs. Forward to the wall, back with
# the wheels one way, forward with them the other: that is one cycle,
# and each pass adds rotation to the one before it. Repeating it is a
# multi-point turn.
#
# A ceiling, not a target. The loop ends the moment the exit test is
# satisfied -- as many cycles as the bay needs and no more -- and this
# is only what stops it going on for ever.
#
# It has to exist. Each cycle reverses SALIDA_RETROCESO_CM, there is a
# wall behind, and a bay that never satisfies the test would otherwise
# walk the robot backwards into it one cycle at a time. Ten cycles is
# up to 90 cm of accumulated reverse; the stall detector is what keeps
# that from becoming a push, and reaching this ceiling means the test is
# asking for something the bay does not offer.
SALIDA_CICLOS = 10

# Distance ahead, in centimetres, that counts as being out.
#
# What phase 3 drives towards: it keeps going while the nose swings
# round and ends the moment the front reads this or more. Also what the
# end-of-run summary counts, to say how many of the cycles finished with
# the way clear.
SALIDA_LIBRE = 40

# Chain straight into the obstacle challenge once the robot is out.
#
# This is the competition sequence: the run starts parked, leaves the
# bay, and goes racing. Splitting it across two programs would mean a
# second steering calibration, a second gyroscope calibration and a
# second press of the start button, in the middle of what the rules
# treat as one run.
#
# salida.py calls obs_ard.correr() with the robot it already prepared,
# so none of that happens twice. It checks the space in front first:
# with the robot still boxed in, starting a race is driving into a wall.
#
# The start button is still pressed before the race. What chaining
# removes is the setup that would be repeated -- the two calibrations,
# which take about a minute between them and need the robot held still.
# The button is not setup: it is where a person decides the robot is
# placed and the run can begin, and that decision stays theirs.
SALIDA_SEGUIR_CON_OBSTACULOS = True

# What "completely out" means, and it takes more than the front sensor.
#
# SALIDA_LIBRE on its own says nothing is straight ahead. A robot still
# wedged across the bay, with a wall on each side and a gap in front,
# passes that test and is not out of anything. Starting a race there
# means the first steering command puts a front wheel into a wall.
#
# So the lateral pair get a say after all, for this one decision -- but
# only ONE side has to be clear, not both. In a one metre corridor
# something is always close on one side, and requiring both rejected a
# robot that had plainly got out: frente 54, izquierda 74, derecha 12,
# which is the corridor with the right-hand wall alongside.
#
# What this rules out is being WEDGED: walls on both sides at once.
# Distancia que el sensor DERECHO tiene que ver para dar paso a la
# carrera, en centimetros.
#
# Esta es la regla de salida, y es una sola: el robot repite ciclos
# hasta que su lado derecho se abre. Sale del hueco hacia ese lado, asi
# que es el primero que deja de ver pared cuando de verdad esta fuera,
# y es el unico sensor que distingue "ya estoy en el pasillo" de "sigo
# en el cajon apuntando a un hueco".
SALIDA_LIBRE_DERECHA = 15

# Seconds the clear reading has to hold before it is believed.
#
# A single frame is a coincidence. The robot is turning while these
# readings are taken, so the front sensor sweeps across the scene and
# will pass over a doorway, a gap between pillars, or simply a patch of
# floor that returns no echo. Any of those reads as open for an instant.
#
# Requiring the whole window to stay clear costs half a second and is
# the difference between measuring an opening and catching a glimpse of
# one.
SALIDA_CONFIRMAR_SEGUNDOS = 0.5



# Detecting the wall behind, without a sensor behind.
#
# The reverse is blind and timed, and there IS something back there. The
# encoder is the instrument that notices: if the wheels stop turning
# while the motor is still being told to turn them, the robot is pushing
# against something rather than moving.
#
# Speed regulation makes this sharper, not vaguer. In 'velocidad' mode
# the controller raises power to hold the commanded speed, so a wheel
# held still is a wheel being pushed harder -- the encoder reading flat
# is unambiguous.
#
# Checked over a window rather than between consecutive samples, because
# at 1.5 cm/s two samples 20 ms apart differ by a fraction of a degree
# and every window would look like a stall.
SALIDA_ATASCO_VENTANA = 0.4     # seconds
SALIDA_ATASCO_GRADOS = 2        # degrees of motor expected in that window

# Seconds of grace before the detector starts looking.
#
# It has to exist, and the track proved it: a reverse reported
# "atascado: 0.34 cm de 10.0" with nothing behind the robot at all. At
# 2 %% the motor takes a moment to come up to speed, and during that
# moment a stalled wheel and a starting one look identical.
#
# The threshold above came down with this. 0.4 s at 2 %% should give 12
# degrees, but the drive train has twice been measured delivering 57 %%
# of what it is asked, so the real figure is nearer 7 and a threshold of
# 4 was inside the noise. 2 is a wheel that is genuinely not turning.
SALIDA_ATASCO_GRACIA = 0.5


_SALIDA_RETROCESO_CM_S = (abs(SALIDA_VELOCIDAD_RETROCESO) / 100.0 * 1560.0
                          / 360.0 * _SALIDA_CIRCUNFERENCIA_CM)
SALIDA_RETROCESO_TIEMPO_MAXIMO = (SALIDA_RETROCESO_MARGEN_TIEMPO
                                  * SALIDA_RETROCESO_CM
                                  / _SALIDA_RETROCESO_CM_S)


# The exit phase runs in two stages.
#
#   front closer than SALIDA_SALIR_LIBRE_CM -> SALIDA_VELOCIDAD_SALIDA
#   front clear of it                       -> SALIDA_VELOCIDAD_SALIDA_RAPIDA
#
# Why: the phase starts with the robot a few centimetres from the wall
# it has just been nosing into, and ends somewhere out in the corridor.
# One speed cannot suit both. Slow enough not to hit the wall it starts
# beside is slow enough to make the rest of the drive take longer than
# it needs to, four times over in four cycles.
#
# The threshold is read from the FILTERED front value, not the raw one.
# Speeding up is the decision that can afford to wait a frame, and it
# should not be taken on a single reading that happened to come back
# long.
SALIDA_SALIR_LIBRE_CM = 10
SALIDA_VELOCIDAD_SALIDA_RAPIDA = 20


# --------------------------------------------------------------------
# salida2.py: the other way out of the bay
# --------------------------------------------------------------------
#
# A second, simpler manoeuvre, kept beside the first rather than
# replacing it. One reverse, one turn, one drive out -- no cycles, no
# approach to the wall first.
#
# Where salida.py rocks back and forth gaining angle a pass at a time,
# this one commits: back off far enough to have room, put the wheels on
# the stop and drive out in a single arc. It wants a bay the robot is
# already roughly square in. The first is for the bay that has to be
# worked out of.

SALIDA2_RETROCESO_CM = 4.0

# Which way the wheels go for the drive out. Opposite hand to salida.py,
# which reverses to the right; this one turns left on the way forward.
SALIDA2_LADO = 'izquierda'

SALIDA2_VELOCIDAD_RETROCESO = 8
SALIDA2_VELOCIDAD_SALIDA = 20

# How long the arc lasts, in seconds. The wheels go to SALIDA2_TOPE and
# stay there, and the robot drives forward for this long.
#
# A duration, not a condition. The manoeuvre is one committed arc rather
# than a search: the wheels go over, the robot goes round, and how far
# that gets it is a question for the exit test afterwards rather than
# something the phase watches for.
#
# 5 s at SALIDA2_VELOCIDAD_SALIDA is about 76 cm of ground, and at full
# lock that is a large part of a circle. The front sensor keeps its veto
# throughout, which is the one thing that can cut it short.
SALIDA2_SALIR_SEGUNDOS = 5.0


# Steering lock for salida2's arc, in degrees, as a magnitude.
#
# The mechanism's own limit rather than the declared stop. VOLANTE_TOPE_*
# is 30 a side, and that 30 is a policy set for the races -- a gentler
# line through corners and less scrubbing. Getting out of a bay wants the
# opposite: the tightest arc the linkage can make.
#
# 50.6 is the measured figure, from the free travel of 119 degrees with a
# margin.
#
# fase_salir widens VOLANTE_TOPE_* to this for the length of the arc and
# puts them back afterwards, because Robot.girar() clamps every steering
# command against them and is the single point that must keep doing so.
# Nothing else in the program sees the wider stop.
SALIDA2_TOPE = 50.6


# --------------------------------------------------------------------
# The bay, measured
# --------------------------------------------------------------------
#
# Bay 38 cm, robot 25.5 cm, parked centred:
#
#     (38 - 25.5) / 2 = 6.25 cm free at each end
#
# That is the number every distance in this manoeuvre has to respect,
# and not knowing it is why the earlier ones failed. A reverse of 10 cm
# was being asked for in a 6.25 cm gap, so the stall detector was not
# misfiring on the motor's start-up after all -- it was finding the back
# wall, correctly, and saying so.
#
# The reverses are now 4 cm, leaving 2.25 cm of margin at the back.
#
# 12.5 cm of total slack is what the whole manoeuvre has to work with.
# That is what salida.py's multi-point turn is for: many small passes,
# each gaining a little angle. salida2.py's single committed arc wants
# room this bay does not have, and is the wrong tool here unless the
# robot can already point most of the way out.
BAHIA_LARGO_CM = 38.0
ROBOT_LARGO_CM = 25.5
BAHIA_HOLGURA_CM = (BAHIA_LARGO_CM - ROBOT_LARGO_CM) / 2.0


# When a sensor loses its echo for longer than ARD_RETENCION, estimate
# it from the other sensor on the same side instead of declaring no wall.
#
# The two sensors on a side look at the SAME wall, one perpendicular and
# one at 25 degrees, so r25 = r90 / cos(25) = 1.103 * r90. That is the
# same geometry the centring error is built from, so it introduces no
# new assumption: if the robot is far from parallel, both readings are
# wrong together and the estimate is no worse than what it replaces.
#
# Why it matters. Substituting ARD_DISTANCIA_MAXIMA drops 100 cm into
# one side of an error summed from four readings, which swings that
# error by about as much. A track run measured the cost: the left 25
# degree sensor lost its echo on 777 frames of 3483, 22 % of the run,
# and the centring error reached -183 and +181 in a corridor where it
# cannot physically exceed about 100. The steering sat on its stop for
# most of the race, following the substitution instead of the wall.
#
# The partner is only used when it has a real recent reading. Two dead
# sensors on one side still mean no wall.
ARD_ESTIMAR_PAREJA = True


# A silent front sensor means WALL, not clear.
#
# The front has no partner to be estimated from, and for it the two
# possible substitutions are not equally safe.
#
# An ultrasonic aimed obliquely at a wall gets no echo: the pulse
# reflects away instead of returning. So the front sensor falls silent
# exactly when the robot reaches a wall at an angle -- when its reading
# matters most -- and again below about 2 cm, when the wall is as close
# as it can be. Silence means wall in both cases, and substituting
# ARD_DISTANCIA_MAXIMA tells the robot the opposite.
#
# That is what happened on track: the front lost its echo, the filter
# reported 100 cm, the collision guard stopped reacting to a wall that
# was still there, and the run was saved by someone picking the robot
# up.
#
# With this on, a silent front keeps its last good reading -- which is
# pessimistic, so safe -- for ARD_FRENTE_PESIMISTA_S beyond the usual
# hold. Past that the silence probably is an empty corridor, since a
# wall does not stay unmeasurable for seconds while the robot moves, and
# the normal substitution takes over. A robot that creeps for ever
# because of one stale reading is no use either.
ARD_FRENTE_PESIMISTA = True
ARD_FRENTE_PESIMISTA_S = 3.0


# --------------------------------------------------------------------
# Leaving the bay by camera
# --------------------------------------------------------------------

# Use the HuskyLens as a second way of deciding the robot is out.
#
# The ultrasonic test has a weakness the camera does not share: an
# ultrasonic aimed obliquely at a wall gets no echo, so the readings go
# unreliable exactly while the robot is turning out of the bay. A camera
# does not care what angle it sees a marker from.
#
# The idea: learn the bay wall on the HuskyLens as an ID of its own.
# While the robot is in the bay that marker is in frame; once it is out
# and pointing down the corridor, it is not. The marker leaving the
# frame is then the signal to stop cycling.
SALIDA_USAR_CAMARA = True

# The ID the bay marker is learned as. It has to be taught on the camera
# itself -- the program cannot create it. `check_hw.py husky` with the
# marker in front prints the ID it was given.
SALIDA_ID_BAHIA = 3

# Narrowest detection, in pixels of frame width, that counts as the bay
# marker. Anything narrower is reported under the right ID and ignored.
#
# Why it exists: the ID on its own is not evidence. Change the lighting
# and the camera starts reporting the learned colour dozens of times a
# run from patches of wall, floor and reflection that are not the
# marker. Every one of those says "still in the bay", the exit is never
# confirmed, and the robot cycles until the total timeout with no way to
# tell it that it got out.
#
# Width is what separates them. The marker, seen from inside the bay,
# fills a good part of a 320 pixel frame; the false ones are small. The
# same reasoning is already used against a different problem in
# angulo_esquive_retenido, where width is what tells one block from
# another.
#
# > [!IMPORTANT]
# > The two ways of getting this wrong are NOT equally bad.
# >
# > Too low is the harmless one: the filter lets noise through and the
# > robot behaves as it did before this line existed.
# >
# > Too high is not: genuine sightings get discarded, the robot decides
# > it is out while it is still in the bay, and with
# > SALIDA_SEGUIR_CON_OBSTACULOS on it goes straight into the race from
# > inside the bay. Start low and raise it.
#
# 20 is a starting guess, not a measurement -- about 6 % of the frame.
# Each cycle prints the width of what it saw, accepted or discarded, so
# one run gives the two ranges and the number to put between them.
SALIDA_BAHIA_ANCHO_MINIMO = 20

# > [!IMPORTANT]
# > Absence is weaker evidence than presence, and this rule is built on
# > absence.
# >
# > A marker can leave the frame because the robot got out, which is
# > what we want to detect -- or because the robot turned past it, or it
# > fell into shadow, or the camera dropped a frame. All four look
# > identical from here.
# >
# > What makes it usable is the window: SALIDA_CONFIRMAR_SEGUNDOS
# > applies, so the marker has to be gone continuously rather than for
# > an instant.
# >
# > With this on, the camera decides ALONE and the ultrasonic test is
# > not consulted. That is the point: an ultrasonic seen obliquely gives
# > no echo, so the lateral readings are least trustworthy exactly while
# > the robot turns out of the bay. One run had a sensor silent on 22 %%
# > of frames and an exit test that three runs running refused to
# > satisfy.
# >
# > Set this False, or leave the marker untaught, and the ultrasonic
# > test decides as before.


# Seconds the whole bay manoeuvre may take before giving up.
#
# The backstop for cycling with no count. With the camera deciding there
# is no arbitrary number of passes to stop at -- and stopping at an
# arbitrary number was what left the robot half out on earlier runs --
# so this is what ends a manoeuvre that is getting nowhere.
#
# It is not the normal ending and should never be reached. The ordinary
# ones are the marker leaving the frame, the back button, and the stall
# detector meeting the wall behind.
SALIDA_TIEMPO_TOTAL_MAXIMO = 180.0
