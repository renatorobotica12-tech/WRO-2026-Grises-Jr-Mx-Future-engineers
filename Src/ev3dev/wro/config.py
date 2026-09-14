"""Robot configuration: ports, wiring and gains.

Everything that needs adjusting at the track should live in this file.

Most values here are measured rather than chosen. Where that is the case
the comment says how it was measured and what the number means, because
a tuning value with no recorded reasoning is one nobody dares change.
"""

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
# steering ran out of angle on track. Then at 45, set by eye. This 50.6
# is what `check_hw.py topes` computes from the measurement above: a
# measured value, not an estimate.
VOLANTE_LIMITE = 50.6

# Per-side clamp, as a FRACTION of VOLANTE_LIMITE.
#
#   1.0  -> the full limit towards that side
#   0.3  -> only 30 %
#   0.0  -> no turning towards that side at all
#
# Fractions rather than degrees so VOLANTE_LIMITE stays the mechanical
# ceiling -- the one that comes from measuring the stops -- and these two
# are the tuning knob. Changing the limit rescales both sides at once.
#
# What it is for: capping how far the robot can cut towards one side
# without touching the other. It affects EVERYTHING that moves the
# steering, both wall following and camera avoidance, because the clamp
# is applied in Robot.girar(), which is the single point both pass
# through.
#
# The sign convention is set by VOLANTE_SIGNO: a positive command turns
# RIGHT.
VOLANTE_FRACCION_DERECHA = 1.0
VOLANTE_FRACCION_IZQUIERDA = 1.0

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
VOLANTE_KP_OBSTACULOS = 1.5

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

# 0 to 100 in both modes. In 'velocidad' it is a percentage of the 1560
# deg/s the medium motor delivers, so 50 means 780 deg/s SUSTAINED, not
# "50 % power and whatever that gives".
#
# The faster it goes, the less time the steering has to correct each
# deviation. If it starts weaving, the first thing to lower is
# VOLANTE_KP, not the speed.
VELOCIDAD = 70                      # open challenge

# Obstacle challenge speed. DECOUPLED from the one above: it runs slower
# on purpose, because the camera has to see the block, decide which side
# to pass, and fit the whole detour in before reaching it. At the open
# challenge speed the robot arrives on top of the block without having
# finished going around it.
VELOCIDAD_OBSTACULOS = 40

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

# Console telemetry for obs_ard.py.
#
# Rate limited on purpose: the loop runs at about 40 Hz, and writing 40
# lines a second over ssh on a Bluetooth link slows down the very loop it
# is trying to measure. At 4 Hz it is still readable and stays out of the
# way.
OBS_TELEMETRIA = True
OBS_TELEMETRIA_HZ = 4
