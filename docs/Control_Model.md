# 🧮 Mathematical Control Model

<div align="center">

**Los Grises Jr — WRO 2026 Future Engineers**

*Every constant in this document is traceable to a measurement on the
robot or to a line in `Src/ev3dev/wro/config.py`.*

</div>

---

## 📐 1. Wall-Centring Geometry

### 1.1 Why four sensors and not two

The robot carries two ultrasonic sensors per side: one perpendicular to
the chassis (90°) and one angled 25° from perpendicular.

Let the corridor width be $W = 100\ \text{cm}$ and let $d$ be the robot's
lateral displacement from the centre line, positive towards the left
wall.

The perpendicular sensors measure:

$$r_{90}^{L} = \frac{W}{2} - d \qquad r_{90}^{R} = \frac{W}{2} + d$$

The angled sensors measure along a beam tilted 25°, so their range is the
perpendicular distance divided by $\cos 25°$:

$$r_{25}^{L} = \frac{1}{\cos 25°}\left(\frac{W}{2} - d\right) \qquad
r_{25}^{R} = \frac{1}{\cos 25°}\left(\frac{W}{2} + d\right)$$

with $\dfrac{1}{\cos 25°} = 1.103$.

### 1.2 The error signal

Each side is summed, and the error is the negated difference:

$$e = -\Big[(r_{90}^{L} + r_{25}^{L}) - (r_{25}^{R} + r_{90}^{R})\Big]$$

Substituting:

$$e = -\Big[(1 + 1.103)\left(\tfrac{W}{2} - d\right) - (1 + 1.103)\left(\tfrac{W}{2} + d\right)\Big]$$

$$\boxed{\;e = 2\,(1 + 1.103)\; d = 4.21\,d\;}$$

**The error is about 4.2 times the physical displacement.** All four
sensors move at once — two approach the wall while two recede — so their
contributions add rather than cancel.

> [!IMPORTANT]
> **Verification.** The model predicts $e = 42$ for a 10 cm displacement.
> Measured on track, a 10 cm displacement produces an error of
> approximately 40. The 5 % difference is consistent with the sensors'
> own tolerance.

### 1.3 Why the negation

If the robot drifts towards the **left** wall, $d > 0$, the left readings
fall, and $e$ comes out **positive**. A positive steering command turns
**right**, away from the wall. The sign closes the loop; without the
negation the robot would steer into the wall it is already approaching.

---

## 🎮 2. The Wall-Centring Controller

### 2.1 Control law

$$\delta = \mathrm{clamp}\big(K_p \cdot e,\; -L_{\text{izq}},\; +L_{\text{der}}\big)$$

where $\delta$ is the steering angle in motor degrees relative to centre,
$K_p$ is the proportional gain, and $L$ is the per-side steering limit.

**There is no derivative or integral term.** That is a measured decision,
not an omission: the tuning log in
[`Logs_Tuning.md`](Logs_Tuning.md) records the integral term saturating
the steering actuator on track imperfections.

### 2.2 Saturation: what the gain actually means

A proportional controller is only meaningful up to the point where it
saturates. That point is:

$$e_{\text{sat}} = \frac{L}{K_p}$$

and, using the geometry of §1.2, the physical displacement that causes
saturation:

$$d_{\text{sat}} = \frac{e_{\text{sat}}}{4.21} = \frac{L}{4.21\,K_p}$$

With the measured limit $L = 50.6°$:

| $K_p$ | $e_{\text{sat}}$ | $d_{\text{sat}}$ | Character |
|:---:|:---:|:---:|:---|
| 10 | 5.1 | **1.2 cm** | Effectively bang-bang |
| 3 | 16.9 | **4.0 cm** | Narrow proportional band |
| 1.5 | 33.7 | **8.0 cm** | Wide proportional band |
| 0.47 | 107 | — | Never saturates in a 1 m corridor |

`config.py` computes $e_{\text{sat}}$ automatically as
`VOLANTE_ERROR_TOPE`, so the meaning of the gain sits next to the gain
itself.

> [!WARNING]
> **A gain can silently compensate for broken hardware.** We ran
> $K_p = 10$ for a period while one ultrasonic sensor was dead. With that
> sensor's readings substituted by the filter, the error sat at a
> constant $+62$ — nearly four times the saturation point — and the
> steering was pinned at full lock regardless of the walls. The gain was
> masking the fault, not solving it. After repair the true operating
> error was 5 to 9, and $K_p = 10$ saturated permanently.

### 2.3 Speed and correction distance

At loop rate $f$ and forward speed $v$, the robot travels

$$\Delta s = \frac{v}{f}$$

between consecutive steering updates. With the measured $f \approx 30\ \text{Hz}$,
each correction covers 33 ms of travel. Raising $v$ without raising $f$
increases $\Delta s$, which is why a faster robot needs a higher gain for
the same correction to arrive in time — and why, past a point, weaving is
a symptom of the loop rate rather than the gain.

---

## 👁 3. Camera Avoidance

### 3.1 Image coordinates

The HuskyLens reports a bounding box in a $320 \times 240$ image. The
horizontal coordinate is re-centred:

$$X = X_{\text{raw}} - 160 \qquad X \in [-160,\, +160]$$

so $X < 0$ is left of frame centre and $X > 0$ is right.

### 3.2 Control law

The controller drives the block towards a **target position in the
image**, one per colour:

$$\delta_{\text{cam}} = \mathrm{clamp}\!\left(\frac{L}{160}\,(X - X_{\text{target}}),\; \text{lo},\; \text{hi}\right)$$

The gain is fixed by geometry rather than tuned:

$$\frac{L}{160} = \frac{50.6}{160} = 0.316\ \text{degrees per pixel}$$

| Colour | ID | $X_{\text{target}}$ | Block ends up | Robot passes |
|:---|:---:|:---:|:---|:---|
| Red | 1 | $-150$ | Left of frame | **Right** of the pillar |
| Green | 2 | $+150$ | Right of frame | **Left** of the pillar |

The inversion is not a sign error. The camera looks where the robot is
**going**: to leave a pillar on your left, you must be pointing to the
right of it.

### 3.3 Why the target must lie inside ±160

The block's position is bounded by the image: $|X| \le 160$. For the
controller to converge, there must exist a reachable $X$ with
$\delta_{\text{cam}} = 0$, which requires

$$\boxed{\;|X_{\text{target}}| \le 160\;}$$

If $X_{\text{target}} = 180$, then even at the extreme $X = 160$:

$$\delta_{\text{cam}} = 0.316 \times (160 - 180) = -6.3°$$

The steering never straightens while the block is in view. It keeps
turning until the pillar leaves the frame — which with a wide-angle lens
takes a long time.

At $X_{\text{target}} = 150$ the proportional band is
$X \in [-10,\, 150]$, covering most of the image, and the loop closes at
$X = 150$.

### 3.4 Measured convergence

A single avoidance, sampled at 4 Hz:

| $X$ | $\delta_{\text{cam}}$ |
|---:|---:|
| $+116$ | $-7.6$ |
| $+127$ | $-4.1$ |
| $+133$ | $-2.2$ |
| $+139$ | $-0.3$ |
| $+143$ | $+0.9$ |

$X$ climbs monotonically towards the target, $\delta$ shrinks to zero and
crosses sign. The loop closes as the model predicts.

---

## 📡 4. Sensor Dropout Filtering

### 4.1 The sentinel problem

When a sensor receives no echo the firmware reports $125$ and clears its
validity bit. **125 is a sentinel, not a distance.**

If it is treated as a distance, a dropout on one side changes that side's
sum by

$$\Delta = 125 - r_{\text{actual}}$$

With a typical $r_{\text{actual}} \approx 20\ \text{cm}$, that is
$\Delta \approx 105$ — more than six times $e_{\text{sat}}$ at
$K_p = 3$. The steering goes to full lock instantly.

**Measured with the robot standing still:** the error swung from $+5$ to
$-82$ and back to $+31$ in under one second.

### 4.2 The three-state filter

Per sensor, with $t_g$ the time of the last good reading:

$$
r_{\text{used}} =
\begin{cases}
r & \text{valid, and } r < 125 \\[4pt]
r_{\text{last good}} & t - t_g \le T_{\text{hold}} \\[4pt]
r_{\max} & t - t_g > T_{\text{hold}}
\end{cases}
$$

with $T_{\text{hold}} = 0.5\ \text{s}$ and $r_{\max} = 100\ \text{cm}$.

A rolling median of three then removes isolated spikes that arrive with
their validity bit set.

### 4.3 The substitution count as a health metric

Every run reports how many substitutions each sensor required. Expressed
as a rate:

$$\rho_i = \frac{n_{\text{sub},i}}{n_{\text{frames}}}$$

Measured across runs: $\rho \approx 0$ for healthy sensors, and
$\rho = 0.25$ to $0.34$ for the faulty one. **A sensor above a few
percent is a hardware fault**, and no gain compensates for a quarter of
its readings being fabricated.

---

## 🧭 5. Heading and Corner Counting

### 5.1 Integration

The AbsoluteIMU reports angular rate. Heading is the discrete integral:

$$\theta_k = \theta_{k-1} + \omega_k\,\Delta t_k, \qquad
\omega_k = \big(\text{raw}_k - \bar{b}\big)\cdot s$$

$\Delta t_k$ is the **measured** elapsed time, not the nominal loop
period, so a varying loop rate does not bias the result.

### 5.2 The scale factor

$$s = 0.1$$

This is exact by construction, not fitted: the `ms-absolute-imu` driver
in GYRO mode reports `units = d/s` with `decimals = 1`, so the raw
integer is ten times the value in degrees per second.

**Independent check.** Integrating one full manual rotation gave
$s = 0.09795$, within 2 % of the exact value. The exact figure is kept;
the measurement served to confirm the axis and the sign.

### 5.3 Bias calibration

The zero offset is the mean of $N = 600$ stationary samples:

$$\bar{b} = \frac{1}{N}\sum_{k=1}^{N}\text{raw}_k$$

Averaging reduces the uncertainty of the bias estimate by
$\sqrt{N} = 24.5$. This matters because bias error integrates: a residual
$\varepsilon$ produces drift $\varepsilon\,t$, growing without bound over
a three-lap run.

### 5.4 Dead band

$$\omega_{\text{used}} = \begin{cases} 0 & |\omega| < 0.3\ °/\text{s} \\ \omega & \text{otherwise}\end{cases}$$

Any residual bias below $0.3\ °/\text{s}$ contributes exactly zero while
the robot drives straight, bounding drift rather than merely reducing it.

### 5.5 Corner detection

A corner is counted when

$$|\theta| \ge 87° \quad \text{and} \quad t - t_{\text{last}} \ge 1.5\ \text{s}$$

after which $\theta$ is reset to zero.

**The 87° threshold**, rather than 90°, absorbs the small undershoot from
the dead band and from discrete integration.

**The 1.5 s interval** exists because the gyroscope cannot distinguish a
track corner from an avoidance manoeuvre. When the camera sends the
steering to full lock, the robot genuinely rotates and genuinely
accumulates 87°.

> [!CAUTION]
> **Measured failure.** During an obstacle run, two corners were counted
> **1.1 s apart**, where real corners were arriving every **6 s**. Each
> false corner brings the target of twelve closer; the robot would brake
> mid-track believing it had completed three laps.

The rejected turn still resets $\theta$, because that rotation physically
happened and carrying it forward would trigger the following corner early.

---

## ⚙️ 6. Steering Kinematics

### 6.1 Travel measurement

The steering is driven against both mechanical stops. Two distinct
quantities result:

| Quantity | Measured | Meaning |
|:---|---:|:---|
| $T_{\text{forced}}$ | $153°$ | Stop to stop at 100 % duty |
| $T_{\text{free}}$ | $119°$ | Reached at minimum duty |

The difference $T_{\text{forced}} - T_{\text{free}} = 34°$ is **not
steering**. It is the mechanism flexing against the stops under load, and
it does not translate into wheel angle.

### 6.2 Deriving the limit

$$L = \frac{T_{\text{free}}}{2} \times 0.85 = \frac{119}{2}\times 0.85 = 50.6°$$

The factor 0.85 leaves a 15 % margin so the steering does not strike the
stops on every correction.

Taking the limit from $T_{\text{forced}}$ would give $65°$, and the
steering would spend the race fighting its own end stops.

### 6.3 Centre

$$c = \frac{p_{+} + p_{-}}{2}$$

the midpoint of the two forced extremes. The forced travel is used here
because both ends are reached the same way; the free ends are reached one
from the centre and one from a stop, and are therefore not symmetric.

### 6.4 Per-side limits

$$L_{\text{der}} = L\cdot f_{\text{der}}, \qquad L_{\text{izq}} = L\cdot f_{\text{izq}}$$

with $f \in [0, 1]$. Expressing the clamp as a fraction keeps $L$ as the
mechanical ceiling and the fractions as the tuning knob, so re-measuring
the mechanism rescales both sides automatically.

---

## 🔋 7. Actuation and Supply Voltage

The EV3 motor output scales with battery voltage, which makes the battery
a hidden control parameter.

Drive speed is commanded as a fraction of the motor's maximum:

$$\omega_{\text{cmd}} = \frac{v_{\%}}{100}\,\omega_{\max}, \qquad \omega_{\max} = 1560\ °/\text{s}$$

**Measured at $v_\% = 80$**, two identical tests minutes apart:

| Battery | Commanded | Achieved | Ratio |
|---:|---:|---:|---:|
| ~7.4 V | 1248 °/s | 1219 °/s | **98 %** |
| ~7.2 V | 1248 °/s | 1093 °/s | **88 %** |

The motor is commanded in **velocity** mode, so the EV3 regulates on the
encoder and compensates for load. It cannot compensate for a supply that
can no longer deliver the required power.

> [!IMPORTANT]
> Gains tuned on a half-charged battery do not reproduce on a full one.
> Battery voltage is recorded before each tuning session.

---

## 📊 8. Constant Reference

Every value below lives in
[`Src/ev3dev/wro/config.py`](../Src/ev3dev/wro/config.py).

| Symbol | Constant | Value | Origin |
|:---|:---|---:|:---|
| $L$ | `VOLANTE_LIMITE` | 50.6° | Derived, §6.2 |
| $K_p$ | `VOLANTE_KP` | 3 | Tuned on track |
| $K_{p,\text{obs}}$ | `VOLANTE_KP_OBSTACULOS` | 1.5 | Tuned on track |
| $e_{\text{sat}}$ | `VOLANTE_ERROR_TOPE` | 16.9 | Derived, §2.2 |
| $s$ | `IMU_ESCALA` | 0.1 | Exact, §5.2 |
| $N$ | `IMU_MUESTRAS_CALIBRACION` | 600 | §5.3 |
| $\omega_{\min}$ | `IMU_ZONA_MUERTA` | 0.3 °/s | §5.4 |
| — | `ANGULO_ESQUINA` | 87° | §5.5 |
| — | `ESQUINA_INTERVALO_MINIMO` | 1.5 s | Measured, §5.5 |
| $T_{\text{hold}}$ | `ARD_RETENCION` | 0.5 s | §4.2 |
| $r_{\max}$ | `ARD_DISTANCIA_MAXIMA` | 100 cm | Corridor width |
| — | `HUSKY_TARGET_ROJO` | −150 px | §3.2 |
| — | `HUSKY_TARGET_VERDE` | +150 px | §3.2 |
| — | `HUSKY_RETENCION` | 0.15 s | Measured |
| — | `HUSKY_MARGEN_ANCHO` | 1.2 | Hysteresis |
| $v_\%$ | `VELOCIDAD` | 70 | Open challenge |
| $v_\%$ | `VELOCIDAD_OBSTACULOS` | 40 | Obstacle challenge |

---

<div align="center">

**Los Grises Jr** · World Robot Olympiad 2026 · Future Engineers

</div>
