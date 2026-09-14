## Engineering Journal
---

### 4 July 2026 – Initial Prototyping & Basic Control Code
We developed the first version of our steering and traction control system for the Open Challenge. The software implemented a PD (Proportional–Derivative) controller using two ultrasonic sensors to keep the robot centered inside the lane. We selected a PD controller because it provides a fast and stable response while avoiding the unnecessary complexity of an integral term for this stage of development.

---

### 8 July 2026 – PCB Manufacturing
To reduce wiring complexity, eliminate loose connections, and improve signal integrity across all sensor channels, we designed a custom PCB for sensor routing and sent it to a manufacturer in China for production.

---

### 10 July 2026 – Hardware Integration
The custom PCB arrived and was successfully assembled. Initial bench tests confirmed reliable power distribution and clean communication signals for the sensor array, significantly improving the electrical reliability and organization of the robot.
---

### 13 July 2026 – Advanced Control Software & FSM Implementation

We developed the first beta version of our Finite State Machine (FSM) in MicroPython. The system switches between different driving states, including straight-line PD centering and an asymmetrical open-loop curve-following mode. We implemented an FSM because we believed the robot required decision-making capabilities beyond a traditional feedback controller, allowing it to adapt its behavior according to different driving situations.
---

### 21 July 2026 – Hardware Delay
We continued testing with the beta version of our software while waiting for additional cables that had been ordered and were scheduled to arrive on 22 July 2026.
---

## 21 July 2026 – I²C Communication Development
We programmed the communication system for our custom PCB using the I²C protocol, allowing multiple ultrasonic sensors to communicate efficiently through a simplified wiring architecture.

### 27 July 2026 – Pre-final Hardware Integration
Today, we integrated the sensor multiplexer into the robot, allowing us to remove almost all cables connected to the numbered EV3 input ports. As a result, only one of the original four sensor ports is now required.

We also installed custom 3D-printed mounts for the ultrasonic sensors, improving their alignment, rigidity, and overall integration with the chassis.

Finally, due to development time constraints and the need for rapid testing, we decided to migrate the control software back to EV3-G (EV3 Blocks). To maintain transparency and reproducibility, we will include both the original source code and a pseudocode version in the Source Code (src) section of our repository.
---
### **28 July 2026 – Final Hardware Integration and *The Robot***

Today, we completed the full assembly of our robot and successfully integrated the custom PCB, ultrasonic sensors, and all major hardware components. With its larger structure, it now looks more like an SUV than a regular car.

At first, we were concerned about the robot's dimensions because the competition rules require it to stay within **30 × 30 × 30 cm**. Fortunately, the final measurements are approximately **24 × 23 × 18 cm**, well within the allowed limits.

Another important concern was the robot's center of gravity. To improve stability, we placed the EV3 Brick at the rear of the chassis while positioning the drive motors near the center, resulting in a more balanced weight distribution.

On the software side, we have already developed a significant portion of the codebase. However, the most important milestone still lies ahead: making everything work together reliably. We believe that, with the hardware now complete, software development and testing will be more straightforward. We expect the next stage of development to focus primarily on software integration, reliability, and testing.

---
###  **24 August 2026** – I²C Communication Problems and Hardware Bottleneck

After several weeks of development, I²C became a major problem for us because the Arduino Nano we were using was defective. The board was missing its factory bootloader, and for some reason, we were unable to reinstall it. We tried everything we knew, including several alternative workarounds, but after four weeks, nothing worked.

The solution was to purchase a new Nano. We confirmed that the software itself was working by testing it with a borrowed Nano that did not have the same issue. This allowed us to conclude that the original board was faulty rather than the software being the source of the problem.

Now, we are waiting for the new Nano so we can continue testing the programs and resume the I²C integration.

---

## **28 / August / 2026**
We began testing the robot and tuning the control system on the track. It appears we have found the optimal values; however, we will continue testing. Having successfully completed the Open Challenge, we are now shifting our focus to the Obstacle Challenge.

---

## **06 / September/ 2026**
### **6 September 2026 – IMU Integration for the Obstacle Challenge**

We decided to integrate a LEGO IMU sensor into our robot because our color sensor, which uses an HSV-based configuration, was experiencing noticeable delays, possibly due to its age. These delays could affect the reliability of the robot during the Obstacle Challenge, particularly when precise movement detection is required.

To address this issue, we integrated the IMU into our control system and created a custom My Block to handle its operation. The logic is relatively simple: the IMU monitors the robot's rotation, and once it detects three complete 360-degree rotations, it sends a command to stop the motors and terminate the program.

We are currently planning to use this system as part of our strategy for the Obstacle Challenge. Further testing will be required to determine the accuracy and reliability of the IMU under actual competition conditions.

---

### **12 September 2026 – Migration to ev3dev, and the Nano moved to USB**

We migrated the control software to Python running on **ev3dev**, a Debian Linux distribution for the EV3 brick, and this is now the version we will compete with.

The reason was not novelty. Writing the controller as blocks meant approximating it: the range mapping and the dead band had to be built from whatever blocks were available, and the reasoning behind each constant lived in our heads rather than in the program. In Python each piece is written literally, and — more importantly for us — **every tuning value can carry the measurement it came from** in a comment right next to it.

We also moved the Arduino Nano off the I²C sensor port and onto the brick's **USB port**. We had assumed the I²C was slow because of our wiring. It is not: the EV3 has no I²C hardware at all, it bit-bangs the protocol in software and runs at a few kHz. Over USB at 115200 baud the Nano sends about 110 lines per second, far more than the control loop consumes, and it frees a sensor port as a bonus.

The new firmware sends one line after **every** sensor rather than after every complete sweep, so the EV3 always has the freshest possible reading. The EV3 side discards the stale lines and keeps only the most recent complete one.

---

### **13 September 2026 – The steering was not dead, it was being interrupted**

The robot had a symptom we could not explain: the steering barely turned, no matter how much we raised the gain. We had pushed the proportional gain as high as 10 chasing it.

We first measured the mechanism itself, by pushing the steering against both mechanical stops and recording where it ended up. Two findings came out of that:

**The stop is not where the motor stops moving.** At 40 % duty the steering advances 28 degrees and jams halfway; it takes 100 % to actually reach the stop. Our earlier routine accepted that first stall as the stop, which measured 26 degrees of travel instead of 111 and put the centre almost 50 degrees off.

**Forced travel and free travel are different numbers.** Pushed at full power the mechanism gives 153 degrees; at minimum power it gives 119. Those 34 degrees of difference are the mechanism flexing against the stops, not steering we can use. We now derive the steering limit from the **free** travel with a 15 % margin.

But the real cause was in the software. The steering command was being re-issued on **every** iteration of the control loop, about thirty times a second. That command is persistent — the motor keeps driving to the commanded position on its own — so re-sending it simply restarted the EV3's position controller every 30 ms. The motor never finished its ramp. It advanced a few degrees per loop and never reached the angle we asked for.

What gave it away was that the drive train already had a guard against exactly this, with a comment explaining why. The steering had been written without it.

---

### **13 September 2026 – A dead ultrasonic sensor, and what it had been hiding**

While reading the sensor frame live we noticed the validity mask never showed all five sensors valid. One channel reported the out-of-range sentinel on **every single frame**.

That sensor is one of the two on the right side. Because it never answered, the filter substituted the maximum useful distance for it permanently, which made the right side appear far away at all times. The centring error sat at a constant **+62**, and with our gain the steering was pinned at full right lock for the entire run, regardless of where the walls actually were.

This explained something embarrassing in hindsight: **the gain of 10 we had been running was compensating for a broken sensor.** With the sensor repaired, the real operating error turned out to be between 5 and 9, and a gain of 10 saturated the steering permanently. We brought it back down.

The lesson we are taking from this is about diagnostics rather than about the sensor. Each run now reports how many readings each sensor needed substituted. A sensor failing a quarter of the time is a hardware fault, and no amount of gain tuning compensates for one.

---

### **13 September 2026 – Two microSD cards lost**

We lost two microSD cards in one session. The first became permanently write-protected: the card's own controller had locked itself read-only, which is what SD cards do when their flash wears out or a write is interrupted. It could not be recovered.

The cause was almost certainly us. We had been switching the robot off by disconnecting the battery instead of shutting down properly, and the battery had been running low enough to brown out under motor load. Both of those interrupt writes.

We now shut down properly, and we have started watching the battery voltage. That turned out to matter for more than the card: the EV3's motor output scales with battery voltage, and two identical speed tests run minutes apart gave **98 % and then 88 %** of the commanded speed as the battery sagged. Tuning done on a half-charged battery does not reproduce on a full one.

---

### **14 September 2026 – Making the camera usable**

Three separate problems had to be solved before the camera could steer reliably.

**The adapter's documentation is wrong about its own data.** Its README lists six values in the order `State, ID, X, Y, W, H`. It actually returns **eight** values, ordered `X, Y, W, H, ID, State`. We confirmed it by watching index 5 alternate between 1 and 7 — exactly the codes for "object detected" and "sees none" — with every other value dropping to zero whenever it read 7.

**Reading it the obvious way was too slow.** Eight separate reads took 49 ms, enough to hold the entire control loop down to 20 Hz. Reading the raw 32-byte block in a single call takes 5 ms, and has the side benefit that values from two different frames can never be mixed.

**The camera flickers, and the adapter switches between blocks.** A single lost frame used to hand control straight back to wall following, which at that instant saw a large error and slammed the steering to full lock — we measured it going from +1.9° to +50.6° and back inside 300 ms with the block in view the whole time. Separately, with two pillars visible the adapter does not keep reporting the same one, so the robot received commands for opposite sides on consecutive loops.

We first tried to fix both with one mechanism: holding the last good command for longer. That was wrong, and the measurement showed it clearly. Stretching the window from 0.1 s to 0.3 s **tripled** how often we were acting on held data, from 12 % of loops to 31 %, while the block switching continued exactly as before. The adapter stays on the other block for longer than any window we could justify.

So we split them. The hold window went back to 0.15 s, which is what it is good at — covering the one-to-three-loop dropouts we actually measured. For the switching we used the **width** of the bounding box: the pillars are all identical, so the wider one is the closer one, and the closest is the one that has to be avoided. Control only moves to a different block when the new one looks clearly wider.

---

### **14 September 2026 – Corners that were not corners**

Running a full lap of the obstacle challenge, the robot counted four corners when it had only turned three.

The cause is that our corner detector integrates the gyroscope, and **it cannot tell a track corner from an avoidance manoeuvre.** When the camera sends the steering to full lock to get around a pillar, the robot genuinely turns, and it genuinely accumulates the 87 degrees we use as the corner threshold.

The spacing gave it away: two corners arrived **1.1 seconds apart**, where the real ones had been coming every 6 seconds.

In a race this is fatal rather than cosmetic. Every false corner brings the target of twelve closer, and the robot would brake in the middle of the track convinced it had completed three laps.

We now reject any corner arriving less than 1.5 seconds after the previous one. The accumulated angle is still reset when we reject one, because that turn physically happened and carrying it forward would trigger the next corner early. Each run reports how many were rejected, so we can tell the difference between the filter working and the filter hiding something.

---

### **14 September 2026 – Documentation**

We brought the repository in line with the robot that actually competes. The ev3dev control software, the current Nano firmware and the technical notes are now in `Src/` and `docs/`, and the port list has been corrected against what the brick actually reports rather than what we remembered wiring.

Doing this exposed how far our documentation had drifted from our hardware. The port list had the two motors swapped and the gyroscope and camera on each other's ports. None of it had caused a problem, because the code knew the truth and only the document was wrong — which is exactly why nobody noticed.

