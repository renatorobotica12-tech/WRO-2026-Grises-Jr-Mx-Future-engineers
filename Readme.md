<div align="center">

# 🏎️ LOS GRISES JR
## World Robot Olympiad 2026  
### Future Engineers Category
<p align="center">
  <img src="https://github.com/user-attachments/assets/6422e0d6-8cc2-4bbc-beaf-4bbada98c140" width="700" />
</p>

<br>

![WRO 2026](https://img.shields.io/badge/WRO-2026-005BBB?style=for-the-badge)
![Future Engineers](https://img.shields.io/badge/Future_Engineers-Category-00A86B?style=for-the-badge)
![LEGO EV3](https://img.shields.io/badge/Main_Controller-LEGO_EV3-F7C600?style=for-the-badge)
![Arduino Nano](https://img.shields.io/badge/Coprocessors-2_Arduino_Nano-00979D?style=for-the-badge)
![Custom PCB](https://img.shields.io/badge/Electronics-Custom_PCB-6A5ACD?style=for-the-badge)
![HuskyLens](https://img.shields.io/badge/Vision-HuskyLens_AI-FF4500?style=for-the-badge)

<br>

---

# 📷 Final Competition Robot

**Insert final robot hero image here**

*(Recommended image: front three-quarter view showing the complete vehicle)*

---

### Official Engineering Repository

Documentation of Team Los Grises Jr's autonomous vehicle developed for:
**World Robot Olympiad 2026 — Future Engineers Category**


---

</div>


# 🚗 Project Overview

Our robot is a fully autonomous four-wheel vehicle designed for the **World Robot Olympiad 2026 Future Engineers competition**.

The objective of this project is to develop a reliable autonomous vehicle capable of navigating the competition environment through a combination of:

- Mechanical engineering.
- Embedded electronics.
- Autonomous control algorithms.
- Sensor processing.
- Software architecture.
- Iterative testing and optimization.


The final platform combines:

| System | Implementation |
|:---|:---|
| Steering | Ackermann steering geometry |
| Drive System | Rear-wheel drive |
| Main Controller | LEGO Mindstorms EV3 Brick |
| Coprocessors | 2 Arduino Nano, 1 for the camera and one for the PCB |
| Vision System | HuskyLens AI Camera |
| Distance Measurement | Five ultrasonic sensors |
| Communication | I²C protocol and UART protocol |
| Electronics | Custom-designed PCB |
| Control Algorithm | Adaptive Dual PD Controller |
| Decision System | Finite State Machine |


---

# ⚡ Quick System Overview

<div align="center">

```
                 ┌──────────────────┐               ┌────────────────┐
                 │ HuskyLens Camera │               │   Ultrasonic   │
                 └────────┬─────────┘               │  Sensors (x5)  │
                          │                         └───────┬────────┘
                 │ UART                            │
                 ▼                                 ▼
                 ┌──────────────────┐               ┌────────────────┐
                 │   Arduino Nano   │               │   Custom PCB   │
                 │      (UART)      │               └───────┬────────┘
        └────────┬─────────┘                       │
                 │                                 ▼
                          │                         ┌────────────────┐
                          │                         │  Arduino Nano  │
                          │                         │     (I²C)      │
                          │                         └───────┬────────┘
                 |                                 │
                 └────────────────┬────────────────┘
                 │
                 ▼
                ┌────────────────┐
                │    LEGO EV3    │
                │   Controller   │
                └────────┬───────┘
                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
         ┌──────────────┐                ┌──────────────┐
         │Steering Motor│                │  Drive Motor │
         └──────────────┘                └──────────────┘
```

</div>


The robot uses a distributed architecture where each subsystem performs a specific role:

- The **Arduino Nano** manages sensor acquisition and communication.
- The **EV3 Brick** performs navigation decisions and motion control.
- The **Custom PCB** organizes power distribution and signal routing.
- The **software architecture** coordinates calibration, sensing, and autonomous driving.


---

# 📑 Table of Contents

- [👥 Team](#-team)
- [🚗 Project Overview](#-project-overview)
- [⚡ Quick System Overview](#-quick-system-overview)
- [⭐ Engineering Highlights](#-engineering-highlights)
- [📊 Robot Specifications](#-robot-specifications)
- [📸 Vehicle Gallery](#-vehicle-gallery)
- [🔩 Components and Hardware](#-components-and-hardware)
- [🛠 Mechanical Design](#-mechanical-design)
- [⚡ Electronics](#-electronics)
- [🔌 Custom PCB](#-custom-pcb)
- [💻 Software Architecture](#-software-architecture)
- [🎯 Steering Calibration](#-automatic-steering-calibration)
- [📡 Sensor Calibration](#-sensor-calibration)
- [🎮 Closed-Loop PID Controller](#-closed-loop-pid-controller)
- [🔄 Finite State Machine](#-finite-state-machine)
- [🧠 Engineering Decisions](#-engineering-decisions)
- [📈 Current Performance](#-current-performance)
- [📓 Engineering Journal](#-engineering-journal)
- [📂 Repository Structure](#-repository-structure)
- [🏁 Conclusion](#-conclusion)


---

# 👥 Team


## 📷 Team Photo

<div align="center">

**Insert official team photograph here**

</div>


---

# 👨‍💻 Renato Medina
<p align="center">
<img width="350" height="350" alt="Image" src="https://github.com/user-attachments/assets/dd9e997b-65a7-4909-8207-ea3630b5aff4" />
</p>

## Team Captain

| Information | Details |
|:---|:---|
| Age | 14 |
| Role | Team Captain and Programmer |
| Main Areas | Software, Integration |


### Responsibilities

- 💻 Software Development
- 🤖 Autonomous Navigation Algorithms
- ⚙️ Mechanical Design
- 🔧 Robot Integration
- 🧠 System Architecture
- 📚 Technical Documentation


---

### About Renato

Renato serves as the **Team Captain** and leads the software architecture, autonomous navigation development, project documentation, and system integration of the robot.

His robotics journey began through the **OnStage TMR program**, where he developed a strong interest in autonomous systems, embedded programming, and engineering design.

Since then, he has focused on combining:

- Software development.
- Electronics.
- Mechanical design.
- Control systems.

to create reliable robotic platforms.

For the WRO 2026 season, his objective is to develop a highly reliable autonomous vehicle while expanding his knowledge of embedded systems, control theory, and robotic engineering.

---

# 👩‍🔧 Paulina

## Mechanical & Electronics Designer


| Information | Details |
|:---|:---|
| Role | Mechanical & Electronics Designer |
| Main Areas | Assembly, Electronics, Testing |


### Responsibilities

- 🔩 Mechanical Assembly
- ⚡ Electronics Integration
- 🔌 PCB Installation
- 🧪 Robot Testing
- 📐 Structural Optimization
- 🛠 Cable Organization


---

### About Paulina

Paulina is responsible for the robot's mechanical construction and electronic integration.

Her work focuses on:

- Structural assembly.
- Sensor installation.
- PCB integration.
- Mechanical validation.
- Hardware reliability.


Her contributions have been fundamental in transforming the initial prototype into a competition-ready autonomous vehicle with improved stability and maintainability.


📷 **Insert Paulina working on assembly image here**


---

# 🤝 Team Responsibilities


| Area | Renato | Paulina |
|:---|:---:|:---:|
| Mechanical Design | ✅ | ✅ |
| Robot Assembly | ✅ | ✅ |
| Electronics Integration | | ✅ |
| PCB Installation | ✅ | ✅ |
| Software Development | ✅ | |
| EV3 Programming | ✅ | |
| Arduino Programming | ✅ | |
| Documentation | ✅ | ✅ |
| Testing & Validation | ✅ | ✅ |


---

# ⭐ Engineering Philosophy


> [!IMPORTANT]
>
> The development of Los Grises Jr is based on continuous engineering improvement.
>
> Every subsystem has been tested, analyzed, modified, and optimized with three main objectives:
>
> - Increase reliability.
> - Improve repeatability.
> - Simplify maintenance.


---

# ⭐ Engineering Highlights


The current robot incorporates multiple engineering improvements developed specifically for the **WRO Future Engineers Challenge**.


| Feature | Implementation |
|:---|:---|
| Steering System | Ackermann steering geometry |
| Drive System | Rear-wheel drive |
| Sensors | Five ultrasonic sensors |
| Vision | HuskyLens AI camera |
| Coprocessors | 2 Arduino Nano, 1 for camera and 1 for pcb |
| Electronics | Custom PCB |
| Communication | I²C architecture |
| Steering Calibration | Automatic encoder-based calibration |
| Control | PID Tuned  |
| Software | Modular architecture |
| Sensor Mounting | Custom 3D printed supports |
| Mechanical Design | Optimized weight distribution |


---

<div align="center">

# 📊 Robot Specifications


<div align="center">

| Specification | Value |
|:---|:---|
| Competition | WRO Future Engineers 2026 |
| Robot Type | Autonomous Vehicle |
| Dimensions | 24 × 23 × 18 cm |
| Maximum Allowed Size | 30 × 30 × 30 cm |
| Steering System | Ackermann Steering |
| Drive System | Rear-Wheel Drive |
| Chassis | LEGO Mindstorms EV3 |
| Main Controller | LEGO EV3 Brick |
| Coprocessor | Arduino Nano |
| Vision System | HuskyLens AI Camera |
| Distance Sensors | Five Ultrasonic Sensors |
| Communication Protocol | I²C |
| Custom Electronics | Custom PCB |
| Sensor Supports | 3D Printed |
| Programming Languages | EV3-G & Arduino C++ |

</div>


---

# 📸 Vehicle Gallery


The following images show the final competition vehicle from different perspectives.

These photographs demonstrate:

- Mechanical construction.
- Sensor placement.
- Electronics integration.
- Cable organization.
- Overall vehicle design.


<div align="center">


| Front View | Top View | Right Side |
|:---:|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/69e7b572-94bf-416a-b6c8-c6d912f90fd9" width="250"> | <img src="https://github.com/user-attachments/assets/4440147d-9600-491b-a967-1af42e869efa" width="250"> | <img src="https://github.com/user-attachments/assets/d07e3bec-f223-4d49-a879-2c7a64f843c3" width="250"> |


| Left Side | Rear View | Bottom View |
|:---:|:---:|:---:|
| <img src="https://github.com/user-attachments/assets/36231890-177c-4a6f-8faf-0d1627496dcb" width="250"> | <img src="https://github.com/user-attachments/assets/5d44d4db-c581-44e0-86bb-8d20cec6b4b8" width="250"> | <img src="https://github.com/user-attachments/assets/47117a61-1927-4884-a85a-d80c9e8139e6" width="250"> |


</div>


> [!NOTE]
>
> A demostration video will be added after the final validation tests are completed.


---

# 🔩 Components and Hardware


The robot combines LEGO components with custom embedded electronics to create a modular and reliable autonomous platform.

Each component was selected according to:

- Reliability.
- Compatibility.
- Mechanical integration.
- Software requirements.
- Long-term maintainability.


| Component | Quantity | Function | Status |
|:---|:---:|:---|:---:|
| LEGO EV3 Brick | 1 | Main controller | ✅ |
| EV3 Medium Motor | 1 | Rear-wheel traction | ✅ |
| EV3 Medium Motor | 1 | Ackermann steering | ✅ |
| Ultrasonic Sensors | 5 | Distance measurement | ✅ |
| Arduino Nano | 1 | Sensor acquisition and communication | ✅ |
| HuskyLens AI Camera | 1 | Vision processing | ✅ |
| Custom PCB | 1 | Power and signal distribution | ✅ |
| LEGO Wheels | 4 | Vehicle mobility | ✅ |
| 3D Printed Supports | Multiple | Sensor mounting | ✅ |


---

# 🛠 Mechanical Design


## Design Evolution


The mechanical structure of the robot was developed through multiple iterations focused on:

- Structural rigidity.
- Weight distribution.
- Driving stability.
- Maintenance accessibility.
- Competition compliance.


Rather than modifying only a single prototype, the robot evolved progressively through testing and engineering improvements.

Every redesign addressed specific limitations discovered during previous experiments.

The result is a compact autonomous vehicle designed for reliability and repeatability.


---

## 📷 Mechanical Design Overview


<div align="center">

**Insert chassis evolution image here**

</div>


---

# 📏 Final Dimensions


| Measurement | Value |
|:---|:---:|
| Length | 24 cm |
| Width | 23 cm |
| Height | 18 cm |


The final design remains within the official WRO Future Engineers national competition limit of:

```
30 × 30 × 30 cm
```


The available internal space allows integration of:

- EV3 electronics.
- Arduino coprocessor.
- Custom PCB.
- Sensor wiring.
- Steering mechanism.


---

# ⚖️ Weight Distribution


Achieving a balanced center of gravity was one of the main mechanical objectives.


Instead of concentrating all components in one area, the mass was intentionally distributed throughout the chassis.


## Main Design Decisions


| Component | Position |
|:---|:---|
| EV3 Brick | Rear section |
| Drive Motor | Center area |
| Steering Motor | Above steering mechanism |
| Custom PCB | Near sensor assembly |
| Arduino Nano | Adjacent to PCB |


This configuration improves:

- Acceleration stability.
- Braking behavior.
- Cornering performance.
- Mechanical reliability.


---

# 🔄 Ackermann Steering System


The robot uses an Ackermann-inspired steering mechanism powered by an EV3 Medium Motor.


Unlike differential steering systems, Ackermann geometry allows the vehicle to follow more realistic turning trajectories by reducing tire slip.


## Steering Control Method


The steering motor is controlled using encoder positions instead of continuous rotation.


This provides:

✅ Repeatable steering angles  
✅ Faster response  
✅ Automatic steering centering  
✅ Reduced positioning error  


---

## Steering Protection


The software limits the maximum steering angle to prevent:

- Mechanical overtravel.
- Transmission stress.
- Unnecessary motor load.


---

# 🚗 Rear-Wheel Drive


The vehicle uses a rear-wheel-drive configuration powered by an EV3 Large Motor.


This architecture was selected because it provides several advantages:


| Advantage | Result |
|:---|:---|
| Better weight transfer | Improved acceleration |
| Independent steering system | Less interference |
| Simpler drivetrain | Increased reliability |
| Easier maintenance | Faster repairs |


Separating propulsion and steering makes vehicle behavior more predictable during autonomous navigation.


---

# 📡 Sensor Mounts


All ultrasonic sensors are installed using custom-designed 3D printed brackets.


<div align="center">

📷 **Insert sensor mount image here**

</div>


The supports were designed to:


- Maintain precise alignment.
- Reduce vibration.
- Improve rigidity.
- Simplify installation.
- Guarantee repeatable sensor positioning.


Compared with direct LEGO mounting, the printed supports significantly improve measurement consistency.


---

# ⚡ Electronics


The robot combines LEGO electronics with custom embedded hardware to create a modular electrical architecture.


The system is divided into two main processing units:


| Controller | Responsibility |
|:---|:---|
| LEGO EV3 Brick | Navigation, decision making, motor control |
| Arduino Nano | Sensor acquisition and communication |


This distributed architecture provides:

- Reduced wiring complexity.
- Lower EV3 port usage.
- Easier debugging.
- Better scalability.


---

# 🔌 Electronic Architecture


<div align="center">


```
          Ultrasonic Sensors
              │ │ │ │ │
              ▼ ▼ ▼ ▼ ▼

          ┌────────────┐
          │ Custom PCB │
          └─────┬──────┘
                │

          ┌────────────┐
          │ Arduino    │
          │ Nano       │
          └─────┬──────┘
                │
              I²C

                │

          ┌────────────┐
          │ LEGO EV3   │
          │ Brick      │
          └─────┬──────┘

                │

      Steering Motor + Drive Motor

```

</div>


The architecture separates:

- Sensor acquisition.
- Data communication.
- Decision making.
- Vehicle control.


This modular approach allows each subsystem to be tested independently.


---

# 🔌 Custom PCB


One of the most important improvements during development was the creation of a custom Printed Circuit Board.


During early testing, sensors were connected individually using loose wiring.

Although functional, this approach caused:


❌ Cable clutter  
❌ Difficult maintenance  
❌ Loose connections  
❌ Limited organization  


To solve these problems, a dedicated PCB was designed specifically for this robot.


---

## PCB Functions


The custom PCB provides:


| Function | Purpose |
|:---|:---|
| Power distribution | Organized electrical supply |
| Signal routing | Cleaner connections |
| Sensor interfaces | Easy sensor replacement |
| Arduino interface | Simplified communication |
| Cable management | Improved organization |


---

## PCB Advantages


Compared with individual wiring, the PCB provides:


✅ Cleaner internal organization  
✅ Faster assembly  
✅ Easier troubleshooting  
✅ Higher mechanical reliability  
✅ Reduced accidental disconnections  
✅ Better future expansion capability  


---

<div align="center">


Software Architecture • Calibration Systems • Ultrasonic Sensor Fusion • PID Controller • Safety Logic • Speed Control • Engineering Decisions • Future Improvements • Repository Structure
</div>
# 💻 Software Architecture

The Los Grises Jr software was designed following a modular and iterative engineering approach, where each subsystem has a specific responsibility.

Rather than concentrating all functionality into a single control routine, the system separates the main tasks into independent logical components:

Sensor acquisition — Ultrasonic sensors for distance and positioning.
Sensor fusion — Combination of multiple ultrasonic readings to generate a reliable lateral error.
Obstacle detection — Front ultrasonic sensor used as a safety condition.
Motion control — Closed-loop PID controller for steering correction.
Speed control — Dynamic calculation of the VEL variable according to the driving conditions.
Emergency response — Immediate stop and reverse maneuver when an obstacle is detected within the critical distance.
Hardware initialization — Motor D initialization, which acts as the PCB adapter.

This organization improves:

✅ Code readability
✅ Debugging efficiency
✅ Testing capability
✅ Repeatability
✅ System reliability
✅ Ease of maintenance

🧩 Software Execution Flow
    A[START: Initialize Motor D / PCB Adapter]
        --> B[Read Front Ultrasonic Sensor]

    B --> C{front_dist < 25 cm?}

    C -->|YES: Obstacle Detected|
        D[Stop Motors]
        --> E[Wait a Few Milliseconds]
        --> F[Reverse 0.5 Rotations]
        --> B

    C -->|NO: Normal Driving|
        G[Read Four Ultrasonic Sensors]

    G --> H[Calculate Left/Right Sensor Sums]

    H --> I["ERROR = (Sensor_1 + Sensor_2) - (Sensor_3 + Sensor_4)"]

    I --> J[Calculate / Update VEL]

    J --> K["Apply PID Controller"]

    K --> L[Apply Motor Command]

    L --> B 
---
    
# 📡 Ultrasonic Sensor Fusion

The robot uses multiple ultrasonic sensors to determine its position relative to the surrounding walls.

Instead of relying on a single sensor, the readings are combined into two groups. Each group represents one side of the robot.

The lateral error is calculated as the difference between both groups:

Side_A = Ultrasonic_1 + Ultrasonic_2

Side_B = Ultrasonic_3 + Ultrasonic_4

ERROR = Side_A - Side_B

This approach provides a more stable representation of the robot's lateral position and reduces the influence of individual sensor variations.

The resulting ERROR becomes the primary feedback signal for the PID controller.

# 🎯 Front Ultrasonic Safety System

A dedicated front ultrasonic sensor is used to detect obstacles ahead of the robot.

The system continuously evaluates the measured distance:

IF front_distance < 25 cm

When the distance falls below the critical threshold, normal PID control is temporarily overridden.

The robot:

Stops the motors.
Waits for a short stabilization period.
Reverses 0.5 motor rotations.
Returns to the main control loop.

This creates a safety override that prevents the robot from continuing forward when an obstacle is detected at close range.

# 🎮 Closed-Loop PID Controller

The main motion-control system is based on a closed-loop PID controller.

The controller receives the calculated ultrasonic error and generates the steering correction required to maintain the desired position.

ERROR
  ↓
PID Controller
  ↓
Steering Correction
  ↓
Motor Command

The PID parameters were experimentally tuned using real track testing.

Rather than relying exclusively on theoretical calculations, the team developed and evaluated multiple iterations of the controller. Each iteration was tested, analyzed, modified, and retested until a stable and efficient configuration was achieved.

The final Kp, Ki, and Kd values therefore represent real-world tuning obtained through track validation.

Control concept
error = sensor_difference

derivative = error - previous_error

integral = integral + error

output =
    (KP × error)
    + (KI × integral)
    + (KD × derivative)

The resulting PID output is used to adjust the motor commands while VEL determines the forward-speed component.

#⚡ Dynamic Speed Control

The variable VEL is used to determine the robot's forward speed during normal operation.

Instead of treating speed as a completely independent constant, the program contains a dedicated section responsible for calculating and updating this variable.

This allows the control system to balance speed and stability, maintaining sufficient forward momentum while preserving the responsiveness of the PID controller.

The speed-control logic was also evaluated through repeated track testing to determine an effective operating range.

# 🔄 Main Control Logic

The complete control strategy can be summarized as follows:

                ┌─────────────────────┐
                │        START        │
                └──────────┬──────────┘
                           ↓
                Initialize Motor D
                           ↓
                  Read Front Sensor
                           ↓
                  ┌────────────────┐
                  │ Distance < 25cm?│
                  └───────┬────────┘
                     YES  │  NO
                      ↓   │
              Stop Motors │
                      ↓   ↓
                Short Wait │
                      ↓    │
             Reverse 0.5   │
               Rotations   │
                      │    ↓
                      │  Read 4
                      │ Ultrasonics
                      │    ↓
                      │ Calculate
                      │ Sensor Error
                      │    ↓
                      │ Calculate VEL
                      │    ↓
                      │ Apply PID
                      │    ↓
                      │ Motor Command
                      │    │
                      └────┴───────────┐
                                       ↓
                                Repeat Main Loop
# 🧠 Engineering Decisions

Several design decisions were made based on practical testing rather than theoretical assumptions.

Multiple ultrasonic sensors

Using multiple sensors allows the robot to calculate its lateral error from combined measurements instead of depending on a single sensor.

PID instead of open-loop control

The robot continuously reacts to sensor feedback, allowing it to correct deviations dynamically rather than relying on predetermined motor commands.

Front ultrasonic safety override

Obstacle detection has priority over normal motion control. When the critical distance is reached, the PID-driven movement is interrupted and the robot performs a predefined safety maneuver.

# Track-based PID tuning

The PID parameters were not selected exclusively through simulation. They were refined through repeated real-track testing, making the final controller better adapted to the actual mechanical and environmental conditions of the robot.

# Dynamic velocity

Separating VEL from the PID correction allows the system to control forward motion while independently applying steering corrections.

🚀 Future Improvements

Potential improvements to the current software architecture include:

Automatic ultrasonic sensor calibration and offset compensation.
Filtering of ultrasonic readings to reduce measurement noise.
Adaptive PID parameters depending on track conditions.
Automatic optimization of VEL.
Improved obstacle recovery behavior.
Data logging for post-run PID analysis.
Automatic parameter tuning based on recorded track data.

---
       ┌───────────────────────┐
       │   Ultrasonic Sensors  │
       └───────────┬───────────┘
                   │
                   ↓
       ┌───────────────────────┐
       │   Sensor Fusion       │
       │   ERROR Calculation   │
       └───────────┬───────────┘
                   │
                   ↓
       ┌───────────────────────┐
       │    PID Controller     │
       └───────────┬───────────┘
                   │
                   ↓
       ┌───────────────────────┐
       │     Motor Control     │
       └───────────────────────┘
                   ↑
                   │
       ┌───────────────────────┐
       │    Speed Control      │
       │        VEL            │
       └───────────────────────┘

       ┌───────────────────────┐
       │ Front Ultrasonic      │
       │ Obstacle Detection    │
       └───────────┬───────────┘
                   │
             < 25 cm?
                   │
                   ↓
       ┌───────────────────────┐
       │   Safety Override     │
       │ Stop + Reverse 0.5R   │
       └───────────────────────┘

---

# 🧠 Engineering Decisions


Every major engineering decision was based on testing, analysis, and continuous improvement.


| Decision | Reason | Benefit |
|:---|:---|:---|
| Ackermann Steering | More realistic vehicle geometry | Smoother turns |
| Rear-Wheel Drive | Separates propulsion and steering | Better reliability |
| Encoder Steering | Absolute position control | Repeatable angles |
| Five Ultrasonic Sensors | Increased environmental awareness | Better perception |
| Arduino Nano Coprocessor | Dedicated sensor processing | Reduced EV3 workload |
| I²C Communication | Single communication channel | Cleaner architecture |
| Custom PCB | Organized electronics | Improved maintenance |
| 3D Printed Mounts | Fixed sensor position | Better measurements |
| Modular Software | Independent modules | Easier development |
| Corridor PID Controller | Adaptive driving behavior | Better stability |


---

# 📈 Current Performance


Current testing demonstrates that the robot provides reliable autonomous behavior.


Achievements:


✅ Stable lane-centering  
✅ Smooth steering corrections  
✅ Automatic steering calibration  
✅ Consistent multi-run performance  
✅ Stable Arduino-EV3 communication  
✅ Improved electrical reliability after PCB integration  
✅ Strong mechanical structure for repeated testing  


The current platform provides a reliable foundation for completing future competition objectives.


---

# 📓 Engineering Journal


The complete engineering process is documented in a dedicated engineering journal.


The journal includes:


- Mechanical iterations.
- Hardware modifications.
- Software development.
- Testing procedures.
- Engineering decisions.
- Performance analysis.


📄 Engineering Journal:

```
docs/engineering_journal.md
```


---

# 📂 Repository Structure


```text
.
├── docs
│   ├── engineering_journal.md
│   ├── mechanical_design.md
│   ├── electronics.md
│   └── software.md
│
├── images
│   ├── robot
│   ├── pcb
│   ├── team
│   └── development
│
├── mechanic
│   ├── sensor_mount.stl
│   └── 
│
├── src
│   ├── EV3-G
│   ├── Arduino
│   └── Pseudocode
│
└── README.md

```


---

# 📅 Development Timeline


| Date | Milestone |
|:---|:---|
| 4 Jul 2026 | Initial PD controller prototype |
| 8 Jul 2026 | PCB manufacturing |
| 10 Jul 2026 | PCB assembly and testing |
| 13 Jul 2026 | FSM implementation |
| 21 Jul 2026 | I²C communication completed |
| 27 Jul 2026 | Final hardware integration |
| 28 Jul 2026 | Final robot assembly |


---

# 🙏 Acknowledgements


We would like to thank our mentors, teachers, and everyone who supported the development of this project throughout the WRO 2026 season.


Their guidance, technical advice, and encouragement were essential in transforming an initial concept into a functional autonomous vehicle.


---

# 🏁 Conclusion


The current version of the **Los Grises Jr autonomous vehicle** represents the result of an iterative engineering process involving:

- Mechanical design.
- Electronics development.
- Embedded programming.
- Control theory.
- Autonomous navigation.


Compared with the earliest prototypes, the final platform incorporates:


✅ Custom-designed PCB  
✅ Arduino Nano coprocessor  
✅ Ackermann steering system  
✅ Automatic steering calibration  
✅ Adaptive Dual PD controller  
✅ Modular software architecture  
✅ Improved mechanical reliability  


The project continues evolving toward the completion of the remaining WRO challenges while maintaining the engineering principles that guided the entire development process:


> **Reliability, repeatability, and continuous improvement.**


---

<div align="center">

# 🏎️ Team Los Grises Jr

## World Robot Olympiad 2026  
## Future Engineers Category

</div>
