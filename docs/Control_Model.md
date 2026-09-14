# 🧮 Mathematical Control Model

<div align="center">

**Los Grises Jr — WRO 2026 Future Engineers**

*Sensor fusion · Error · Control law · Kinematics · Torque · Steering geometry*

Every constant here is traceable either to a measurement on the robot or
to a line in [`Src/ev3dev/wro/config.py`](../Src/ev3dev/wro/config.py).
Where a value is an estimate rather than a measurement, it says so.

</div>

---

## 🚗 1. Vehicle Parameters

| Parameter | Symbol | Value |
|:---|:---:|---:|
| Mass | $m$ | **861 g** = 0.861 kg |
| Overall dimensions | — | 24 × 23 × 18 cm |
| Wheel diameter | $D$ | 56.0 mm |
| Wheel radius | $r$ | 28.0 mm = 0.028 m |
| Wheel circumference | $C$ | 175.93 mm |
| Wheelbase | $L_b$ | 24.0 cm |
| Track width | $W_t$ | 18.0 cm |
| Motor encoder resolution | — | 1° |
| Drive motor | — | EV3 Medium, port B |
| Steering motor | — | EV3 Medium, port A |

$$C = \pi D = \pi \times 56.0 = 175.93\ \text{mm}$$

---

## 📐 2. Wall-Centring Geometry

### 2.1 Sensor layout

Four lateral ultrasonic sensors, two per side: one perpendicular to the
chassis (90°) and one angled. A fifth sensor faces forward and is read
but not used in any control decision.

Let the corridor width be $W = 100\ \text{cm}$ and let $d$ be the lateral
displacement from the centre line, positive towards the left wall.

The perpendicular sensors measure:

$$r_{90}^{L} = \frac{W}{2} - d \qquad r_{90}^{R} = \frac{W}{2} + d$$

The angled sensors are mounted at **25° from perpendicular**. Their range
is therefore the perpendicular distance divided by $\cos 25°$:

$$r_{25} = \frac{1}{\cos 25°}\cdot r_{90} = 1.103\,r_{90}$$

### 2.2 The error signal

Each side is summed, and the error is the negated difference between
sides:

$$e = -\Big[(r_{90}^{L} + r_{25}^{L}) - (r_{25}^{R} + r_{90}^{R})\Big]$$

$$e = -\Big[(1 + 1.103)\left(\tfrac{W}{2} - d\right) - (1 + 1.103)\left(\tfrac{W}{2} + d\right)\Big]$$

$$\boxed{\;e = 2\,(1 + 1.103)\,d = 4.21\,d\;}$$

**The error is 4.21 times the physical displacement.** All four sensors
move at once — two approach the wall while two recede — so their
contributions add rather than cancel. This is why the error grows several
times faster than the displacement, and why the proportional gain looks
small next to the numbers involved.

> [!IMPORTANT]
> **Verification.** The model predicts $e = 42$ for a 10 cm displacement.
> Measured on track, a 10 cm displacement produces an error of
> approximately 40 — within 5 %, consistent with sensor tolerance.

### 2.3 Why the negation matters

If the robot drifts towards the **left** wall, $d > 0$, the left readings
fall, and $e$ comes out **positive**. A positive steering command turns
**right**, away from the wall.

The sign is what closes the loop. Without the negation the robot would
steer into the wall it is already approaching.

### 2.4 Decomposing a diagonal reading

A diagonal sensor's range splits into lateral and forward components:

$$Y_{\text{wall}} = D_{\text{diag}}\cos 25° = 0.906\,D_{\text{diag}}
\qquad
X_{\text{forward}} = D_{\text{diag}}\sin 25° = 0.423\,D_{\text{diag}}$$

This is what makes the angled sensors useful: the forward component means
they see a corner slightly before the perpendicular pair does.

---

## 🎮 3. The Wall-Centring Controller

### 3.1 Control law

$$\delta = \mathrm{clamp}\big(K_p \cdot e,\; -L_{\text{izq}},\; +L_{\text{der}}\big)$$

where $\delta$ is the steering angle in motor degrees relative to centre.

**There is no derivative or integral term.** That is a measured decision,
not an omission. The tuning log in [`Logs_Tuning.md`](Logs_Tuning.md)
records the integral term saturating the steering actuator on track
imperfections — corners generate a sustained error for a short period,
the integral accumulates it, and the steering deviates from its
geometric response.

### 3.2 Saturation: what the gain actually means

A proportional controller is only meaningful up to the point where it
saturates:

$$e_{\text{sat}} = \frac{L}{K_p}
\qquad\qquad
d_{\text{sat}} = \frac{e_{\text{sat}}}{4.21} = \frac{L}{4.21\,K_p}$$

With the measured limit $L = 50.6°$:

| $K_p$ | $e_{\text{sat}}$ | $d_{\text{sat}}$ | Character |
|:---:|:---:|:---:|:---|
| 10 | 5.1 | **1.2 cm** | Effectively bang-bang |
| 3 | 16.9 | **4.0 cm** | Narrow proportional band |
| 1.5 | 33.7 | **8.0 cm** | Wide proportional band |
| 0.47 | 107 | — | Never saturates in a 1 m corridor |

`config.py` computes $e_{\text{sat}}$ automatically as
`VOLANTE_ERROR_TOPE`, so the meaning of a gain sits next to the gain.

> [!CAUTION]
> **A gain can silently compensate for broken hardware.** We ran
> $K_p = 10$ while one ultrasonic sensor was dead. With its readings
> substituted by the filter, the error sat at a constant $+62$ — nearly
> four times the saturation point — and the steering was pinned at full
> lock regardless of the walls. After repair the true operating error was
> 5 to 9, and $K_p = 10$ saturated permanently. **The gain had been
> masking the fault.**

### 3.3 Speed and correction distance

At loop rate $f$ and forward speed $v$, the robot travels

$$\Delta s = \frac{v}{f}$$

between consecutive steering updates. At the measured
$f \approx 30\ \text{Hz}$, each correction covers 33 ms of travel.
Raising $v$ without raising $f$ increases $\Delta s$, which is why a
faster robot needs more gain for the same correction to arrive in time —
and why, past a point, weaving is a symptom of the loop rate rather than
of the gain.

---

## ⚙️ 4. Motor Kinematics and Linear Displacement

### 4.1 Distance from motor angle

$$d = \frac{\theta}{360°}\cdot C$$

$$\frac{C}{360} = \frac{175.93}{360} = 0.4887\ \text{mm/degree}$$

$$\theta = \frac{d}{0.4887}$$

The encoder resolves 1°, so the theoretical position quantum is
**0.49 mm** of wheel travel. That is the floor on odometric precision
before slip is considered.

### 4.2 Speed command to linear velocity

Speed is commanded as a percentage of the motor maximum:

$$\omega_{\text{cmd}} = \frac{v_{\%}}{100}\,\omega_{\max},
\qquad \omega_{\max} = 1560\ °/\text{s}$$

Converting to linear wheel speed:

$$v = \frac{\omega_{\text{cmd}}}{360}\cdot C$$

| $v_\%$ | $\omega_{\text{cmd}}$ | $v$ at the wheel |
|---:|---:|---:|
| 40 | 624 °/s | 0.305 m/s |
| 50 | 780 °/s | 0.381 m/s |
| 70 | 1092 °/s | 0.534 m/s |
| 100 | 1560 °/s | 0.763 m/s |

> [!NOTE]
> These assume direct drive from motor to wheel. Any gear reduction
> scales them down proportionally, and should be measured rather than
> assumed.

---

## 🔩 5. Torque, Traction and Acceleration

### 5.1 Available force

The EV3 Medium Motor has a reference running torque of
$\tau = 8\ \text{N·cm} = 0.08\ \text{N·m}$ and a stall torque of
$0.12\ \text{N·m}$. Stall torque is a blocked-rotor figure, not a driving
condition.

$$F = \frac{\tau}{r} = \frac{0.08}{0.028} \approx 2.86\ \text{N}$$

### 5.2 What the mass makes of it

With $m = 0.861\ \text{kg}$:

$$a_{\max} = \frac{F}{m} = \frac{2.86}{0.861} \approx 3.32\ \text{m/s}^2$$

$$W = mg = 0.861 \times 9.81 \approx 8.45\ \text{N}$$

### 5.3 The slip condition

Tractive force cannot exceed what friction can transmit:

$$F \le \mu\,N$$

Taking the full weight on the driven axle as an upper bound:

$$\mu_{\text{required}} \ge \frac{F}{W} = \frac{2.86}{8.45} \approx 0.34$$

Rubber on a smooth competition surface typically gives $\mu$ well above
0.34, so the robot should be **torque-limited rather than
traction-limited** under normal acceleration.

> [!IMPORTANT]
> The rear-wheel-drive layout puts only part of the mass on the driven
> axle, which raises the effective $\mu$ required. This was observed at
> the highest speeds tested, where the chassis began to drift on rear-tyre
> slip — the ideal kinematic model stops being accurate there.

### 5.4 Time to reach speed

$$t = \frac{v}{a_{\max}}$$

| Target | $v$ | $t$ (ideal) |
|---:|---:|---:|
| $v_\% = 40$ | 0.305 m/s | 0.09 s |
| $v_\% = 70$ | 0.534 m/s | 0.16 s |

These are upper-bound figures: they ignore drivetrain losses, rolling
resistance and the motor's own speed-torque curve, all of which reduce
available torque as speed rises.

---

## 🔄 6. Steering Geometry

### 6.1 Ackermann condition

With wheelbase $L_b$ and track width $W_t$, for a commanded steering
angle $\alpha$ the inner and outer wheels must take different angles to
share a turning centre:

$$\delta_{\text{inner}} = \arctan\!\left(\frac{L_b}{\dfrac{L_b}{\tan\alpha} - \dfrac{W_t}{2}}\right)
\qquad
\delta_{\text{outer}} = \arctan\!\left(\frac{L_b}{\dfrac{L_b}{\tan\alpha} + \dfrac{W_t}{2}}\right)$$

The turning radius measured to the centre of the rear axle is

$$R = \frac{L_b}{\tan\alpha}$$

With $L_b = 24.0\ \text{cm}$ and $W_t = 18.0\ \text{cm}$:

| $\alpha$ | $R$ | $\delta_{\text{inner}}$ | $\delta_{\text{outer}}$ |
|---:|---:|---:|---:|
| 10° | 136 cm | 10.7° | 9.4° |
| 20° | 66 cm | 22.0° | 18.4° |
| 30° | 42 cm | 34.0° | 26.9° |

Satisfying this geometry is what stops the inner wheel from scrubbing
through a turn.

> [!WARNING]
> **Open item: $L_b$ and $W_t$ need re-measuring.** The values above,
> 24.0 cm and 18.0 cm, are identical to the robot's overall **length** and
> **height** from the specification table (24 × 23 × 18 cm). Wheelbase is
> measured axle to axle and is necessarily shorter than the vehicle;
> track width is measured between wheel centres. These figures appear to
> have been taken from the bounding box rather than from the chassis.

### 6.2 Steering travel measurement

The steering is driven against both mechanical stops. Two distinct
quantities result:

| Quantity | Measured | Meaning |
|:---|---:|:---|
| $T_{\text{forced}}$ | $153°$ | Stop to stop at 100 % duty |
| $T_{\text{free}}$ | $119°$ | Reached at minimum duty |

The difference of $34°$ is **not steering**. It is the mechanism flexing
against the stops under load; it does not become wheel angle.

### 6.3 Deriving the limit

$$L = \frac{T_{\text{free}}}{2}\times 0.85 = \frac{119}{2}\times 0.85 = 50.6°$$

The factor 0.85 leaves a 15 % margin so the steering does not strike its
stops on every correction. Taking the limit from $T_{\text{forced}}$
would give $65°$, and the steering would spend the race fighting its own
end stops.

### 6.4 Centre and per-side limits

$$c = \frac{p_{+} + p_{-}}{2}$$

the midpoint of the two forced extremes. The forced travel is used
because both ends are reached the same way; the free ends are reached one
from centre and one from a stop, and are therefore not symmetric.

$$L_{\text{der}} = L\,f_{\text{der}} \qquad L_{\text{izq}} = L\,f_{\text{izq}}
\qquad f \in [0,1]$$

Expressing the clamp as a fraction keeps $L$ as the mechanical ceiling and
the fractions as the tuning knob, so re-measuring the mechanism rescales
both sides automatically.

---

## 👁 7. Camera Avoidance

### 7.1 Image coordinates

The HuskyLens reports a bounding box in a $320\times 240$ image. The
horizontal coordinate is re-centred:

$$X = X_{\text{raw}} - 160 \qquad X \in [-160,\,+160]$$

### 7.2 Control law

$$\delta_{\text{cam}} = \mathrm{clamp}\!\left(\frac{L}{160}\,(X - X_{\text{target}}),\;\text{lo},\;\text{hi}\right)$$

The gain is fixed by geometry, not tuned:

$$\frac{L}{160} = \frac{50.6}{160} = 0.316\ \text{degrees per pixel}$$

| Colour | ID | $X_{\text{target}}$ | Block ends up | Robot passes |
|:---|:---:|:---:|:---|:---|
| Red | 1 | $-150$ | Left of frame | **Right** of the pillar |
| Green | 2 | $+150$ | Right of frame | **Left** of the pillar |

The inversion is not a sign error. The camera looks where the robot is
**going**: to leave a pillar on your left, you must point to the right of
it.

### 7.3 Why the target must lie inside ±160

For the controller to converge there must exist a reachable $X$ with
$\delta_{\text{cam}} = 0$, which requires

$$\boxed{\;|X_{\text{target}}| \le 160\;}$$

If $X_{\text{target}} = 180$, then even at the extreme $X = 160$:

$$\delta_{\text{cam}} = 0.316\,(160-180) = -6.3°$$

The steering never straightens while the block is in view. At
$X_{\text{target}} = 150$ the proportional band covers
$X \in [-10,\,150]$ and the loop closes at $X = 150$.

### 7.4 Measured convergence

| $X$ | $\delta_{\text{cam}}$ |
|---:|---:|
| $+116$ | $-7.6$ |
| $+127$ | $-4.1$ |
| $+133$ | $-2.2$ |
| $+139$ | $-0.3$ |
| $+143$ | $+0.9$ |

$X$ climbs monotonically to the target, $\delta$ shrinks to zero and
crosses sign. The loop closes as predicted.

---

## 📡 8. Sensor Dropout Filtering

### 8.1 The sentinel problem

With no echo, the firmware reports $125$ and clears the sensor's validity
bit. **125 is a sentinel, not a distance.** Treated as one, a dropout
changes that side's sum by

$$\Delta = 125 - r_{\text{actual}}$$

With a typical $r_{\text{actual}} \approx 20\ \text{cm}$ that is
$\Delta \approx 105$, over six times $e_{\text{sat}}$ at $K_p = 3$.

**Measured with the robot standing still:** the error swung from $+5$ to
$-82$ and back to $+31$ in under one second.

### 8.2 The three-state filter

$$
r_{\text{used}} =
\begin{cases}
r & \text{valid, and } r < 125 \\[4pt]
r_{\text{last good}} & t - t_g \le T_{\text{hold}} \\[4pt]
r_{\max} & t - t_g > T_{\text{hold}}
\end{cases}
$$

with $T_{\text{hold}} = 0.5\ \text{s}$ and $r_{\max} = 100\ \text{cm}$,
followed by a rolling median of three.

### 8.3 Substitution rate as a health metric

$$\rho_i = \frac{n_{\text{sub},i}}{n_{\text{frames}}}$$

Measured: $\rho \approx 0$ for healthy sensors, $\rho = 0.25$ to $0.34$
for a faulty one. **A sensor above a few percent is a hardware fault**,
and no gain compensates for a quarter of its readings being fabricated.

---

## 🧭 9. Heading and Corner Counting

### 9.1 Integration

$$\theta_k = \theta_{k-1} + \omega_k\,\Delta t_k,
\qquad \omega_k = (\text{raw}_k - \bar b)\,s$$

$\Delta t_k$ is the **measured** elapsed time, not the nominal loop
period, so a varying loop rate introduces no bias.

### 9.2 The scale factor

$$s = 0.1$$

Exact by construction: the `ms-absolute-imu` driver in GYRO mode reports
`units = d/s` with `decimals = 1`, so the raw integer is ten times the
value in degrees per second.

**Independent check.** Integrating one full manual rotation gave
$s = 0.09795$, within 2 %. The exact value is kept; the measurement
confirmed the axis and the sign.

### 9.3 Bias calibration

$$\bar b = \frac{1}{N}\sum_{k=1}^{N}\text{raw}_k, \qquad N = 600$$

Averaging reduces the bias uncertainty by $\sqrt N = 24.5$. This matters
because bias error **integrates**: a residual $\varepsilon$ produces
drift $\varepsilon t$, growing without bound over a three-lap run.

### 9.4 Dead band

$$\omega_{\text{used}} =
\begin{cases} 0 & |\omega| < 0.3\ °/\text{s}\\ \omega & \text{otherwise}\end{cases}$$

Any residual bias below $0.3\ °/\text{s}$ contributes exactly zero while
driving straight, **bounding** drift rather than merely reducing it.

### 9.5 Corner detection

$$|\theta| \ge 87° \quad\text{and}\quad t - t_{\text{last}} \ge 1.5\ \text{s}$$

**87° rather than 90°** absorbs the small undershoot from the dead band
and from discrete integration.

**The 1.5 s interval** exists because the gyroscope cannot distinguish a
track corner from an avoidance manoeuvre: when the camera sends the
steering to full lock, the robot genuinely rotates and genuinely
accumulates 87°.

> [!CAUTION]
> **Measured failure.** During an obstacle run, two corners were counted
> **1.1 s apart**, where real corners were arriving every **6 s**. Each
> false corner brings the target of twelve closer; the robot would brake
> mid-track believing it had finished.

A rejected turn still resets $\theta$, because that rotation physically
happened and carrying it forward would trigger the following corner
early.

---

## 🔋 10. Supply Voltage as a Hidden Parameter

The EV3 motor output scales with battery voltage.

**Measured at $v_\% = 80$**, two identical tests minutes apart:

| Battery | Commanded | Achieved | Ratio |
|---:|---:|---:|---:|
| ~7.4 V | 1248 °/s | 1219 °/s | **98 %** |
| ~7.2 V | 1248 °/s | 1093 °/s | **88 %** |

The drive motor is commanded in **velocity** mode, so the EV3 regulates
on the encoder and compensates for load. It cannot compensate for a
supply that can no longer deliver the power.

> [!IMPORTANT]
> Gains tuned on a half-charged battery do not reproduce on a full one.
> Battery voltage is recorded before each tuning session.

---

## 📊 11. Reference Values

### Physical

| Parameter | Value | Meaning |
|:---|---:|:---|
| Mass | **861 g** | Complete vehicle, as raced |
| Weight | 8.45 N | $mg$ |
| Overall dimensions | 24 × 23 × 18 cm | Within the 30 × 30 × 30 limit |
| Wheel diameter $D$ | 56.0 mm | Drive wheel |
| Wheel circumference $C$ | 175.93 mm | $\pi D$ |
| Linear distance per degree | 0.4887 mm/° | $C/360$ |
| Wheelbase $L_b$ | 24.0 cm | ⚠️ re-measure, see §6.1 |
| Track width $W_t$ | 18.0 cm | ⚠️ re-measure, see §6.1 |
| Motor resolution | 1° | EV3 encoder |
| Running torque | 0.08 N·m | Reference operating torque |
| Stall torque | 0.12 N·m | Blocked rotor, not a driving figure |
| Tractive force | ≈ 2.86 N | $\tau / r$, ideal |
| Max acceleration | ≈ 3.32 m/s² | $F/m$, ideal |
| Required friction | $\mu \ge 0.34$ | Not to slip at full torque |
| Motor max speed | 1560 °/s | EV3 Medium |

### Control

| Symbol | Constant | Value | Origin |
|:---|:---|---:|:---|
| $L$ | `VOLANTE_LIMITE` | 50.6° | Derived, §6.3 |
| $K_p$ | `VOLANTE_KP` | 3 | Tuned on track |
| $K_{p,\text{obs}}$ | `VOLANTE_KP_OBSTACULOS` | 1.5 | Tuned on track |
| $e_{\text{sat}}$ | `VOLANTE_ERROR_TOPE` | 16.9 | Derived, §3.2 |
| — | `VOLANTE_VELOCIDAD` | 600 °/s | Steering slew rate |
| $s$ | `IMU_ESCALA` | 0.1 | Exact, §9.2 |
| $N$ | `IMU_MUESTRAS_CALIBRACION` | 600 | §9.3 |
| $\omega_{\min}$ | `IMU_ZONA_MUERTA` | 0.3 °/s | §9.4 |
| — | `ANGULO_ESQUINA` | 87° | §9.5 |
| — | `ESQUINA_INTERVALO_MINIMO` | 1.5 s | Measured, §9.5 |
| $T_{\text{hold}}$ | `ARD_RETENCION` | 0.5 s | §8.2 |
| $r_{\max}$ | `ARD_DISTANCIA_MAXIMA` | 100 cm | Corridor width |
| — | `HUSKY_TARGET_ROJO` | −150 px | §7.2 |
| — | `HUSKY_TARGET_VERDE` | +150 px | §7.2 |
| — | `HUSKY_RETENCION` | 0.15 s | Measured |
| — | `HUSKY_MARGEN_ANCHO` | 1.2 | Hysteresis |
| $v_\%$ | `VELOCIDAD` | 70 | Open challenge |
| $v_\%$ | `VELOCIDAD_OBSTACULOS` | 40 | Obstacle challenge |
| $f$ | — | ≈ 30 Hz | Measured loop rate |

---

## 🔬 12. Open Items

Values that need a measurement rather than a decision:

| Item | Why it matters | Section |
|:---|:---|:---:|
| Wheelbase and track width | Current figures match the bounding box, not the chassis | §6.1 |
| Gear ratio, motor to wheel | Every linear speed in §4.2 assumes direct drive | §4.2 |
| Mass on the driven axle | Sets the real slip threshold, not the total weight | §5.3 |

---

<div align="center">

**Los Grises Jr** · World Robot Olympiad 2026 · Future Engineers

</div>
