# Vrishab Differential-Drive Rover Controller

Python control software for a two-wheel differential-drive rover using two
Moteus motor controllers and a Moteus Pi3Hat. The main program accepts velocity
commands over UDP, converts them into left/right wheel commands, reads wheel and
IMU feedback, estimates wheel odometry, and sends telemetry to a remote PC.

> **Safety:** Test with the wheels raised off the ground first. Keep an emergency
> stop available. Confirm motor IDs, wheel directions, gear reduction, velocity
> limits, and network addresses before driving the rover.

## Data flow

```text
Remote teleop sender
  UDP :5006 {"linear": ..., "angular": ...}
              |
              v
          turtle.py
              |
              +--> DifferentialDrive.vel_cmd()
              |        |
              |        v
              |   Moteus IDs 1 and 2 via Pi3Hat
              |
              +<-- wheel position/velocity and Pi3Hat IMU
              |
              +--> wheel odometry + IMU telemetry
                       UDP 192.168.10.1:5000
```

The incoming `linear` and `angular` values are expected to be normalized,
normally in the range `-1.0` to `1.0`. If no teleop packet is received for
0.5 seconds, `turtle.py` commands both wheels to stop.

## What each file does

| File | Purpose |
| --- | --- |
| `turtle.py` | Main rover program. Runs motor/IMU readers, receives UDP teleop commands, computes odometry, drives both motors, and transmits telemetry. |
| `agv.py` | Differential-drive kinematics and wheel-odometry calculations. Also contains an angle-unwrapping helper. |
| `moteus_interface.py` | Pi3Hat/Moteus interface for disarming motors, reading motor state and IMU data, and sending velocity commands. |
| `sub.py` | Non-blocking UDP teleop receiver. Reads `linear` and `angular` JSON fields and implements the command timeout check. |
| `joystick.py` | Local Pygame joystick reader with dead-zone handling. Used by the older `main.py` path. |
| `main.py` | Older local-joystick prototype. It does not match the current odometry and IMU APIs; use `turtle.py` for the present system. |
| `sensors.py` | Optional serial magnetometer reader for `/dev/ttyUSB0` at 115200 baud. Magnetometer use is currently disabled in `turtle.py`. |
| `filters.py` | Reusable first-order low-pass filter. |
| `test.py` | Old conversion experiment; its method names no longer match `GearReductionDeg` and it is not the system test. |

## Hardware and software assumptions

- Linux computer (the project is intended for a Jetson-class rover computer)
- Python 3
- Moteus Pi3Hat
- Two Moteus motor controllers, currently IDs `1` and `2`
- Left motor: Moteus CAN ID `1`, connected to the Pi3Hat `JC1` connector
- Right motor: Moteus CAN ID `2`, configured on Pi3Hat bus `2`
- UDP network connection between the rover and control PC
- A compatible gamepad only when using the older `main.py` prototype
- Optional serial magnetometer on `/dev/ttyUSB0`

The Python imports used by this workspace are:

- `moteus`
- `moteus-pi3hat`
- `pygame` (only for joystick operation)
- `pyserial` (only for the optional magnetometer)

Install the packages according to the Moteus/Pi3Hat instructions for the target
computer. A typical Python environment can install the non-hardware packages
with:

```bash
python3 -m pip install pygame pyserial
```

The exact `moteus-pi3hat` installation can depend on the Jetson/Raspberry Pi
platform and should be verified against the hardware vendor's instructions.

## Clone, pull, and update

Clone the repository:

```bash
git clone https://github.com/nileshmetakota-17/Lidar_navigation.git
cd Lidar_navigation
```

Pull the latest changes later:

```bash
cd ~/Lidar_navigation
git pull --ff-only
```

Use `--ff-only` to avoid accidentally creating a merge commit when updating the
rover checkout.

## Differential-drive configuration

The current rover configuration is near the bottom of `turtle.py`:

```python
vrishab = MoteusInterface(servo_bus_map={1: [1], 2: [2]}, can_ids=[1, 2])
converter = GearReductionDeg(6)
rover = DifferentialDrive(
    0.07305,      # wheel radius [m]
    0.291,        # wheel separation [m]
    1.0,          # maximum linear velocity [m/s]
    1.5708,       # maximum angular velocity [rad/s]
    3 * math.pi,  # maximum wheel velocity [rad/s]
)
```

Change these values to match the physical rover:

| Setting | Meaning | Effect of an incorrect value |
| --- | --- | --- |
| `servo_bus_map` | Pi3Hat CAN bus to motor-ID mapping. Bus `1` contains left motor CAN ID `1` on `JC1`; bus `2` contains right motor CAN ID `2`. | A motor may not respond. |
| `can_ids` | Moteus controller IDs: `1` is left and `2` is right. | Commands and feedback may target the wrong motor. |
| `GearReductionDeg(6)` | Motor turns per wheel turn used by the conversion | Wheel speed and odometry scale will be wrong. |
| `0.07305` | Wheel radius in metres | Linear speed and travelled distance will be scaled incorrectly. |
| `0.291` | Centre-to-centre distance between wheels in metres | Turning rate and heading estimate will be wrong. |
| `1.0` | Maximum commanded linear speed in m/s | Sets full-scale response to `linear=+/-1`. |
| `1.5708` | Maximum commanded yaw rate in rad/s | Sets full-scale response to `angular=+/-1`. |
| `3 * math.pi` | Intended wheel-speed limit in rad/s | Currently not enforced because clamping is commented out in `agv.py`. |

Motor direction is configured in two places in `turtle.py`:

```python
left_wheel_velocity = -math.radians(converter.mot2deg(states["left_vel"]))
right_wheel_velocity = math.radians(converter.mot2deg(states["right_vel"]))

vel_cmd = {
    1: -left_wheel_cmd,
    2: right_wheel_cmd,
}
```

The minus signs compensate for mirrored left/right motor mounting. If a wheel
runs backward, change the sign for that same wheel in both feedback conversion
and command output. Do not swap signs in only one location, because commanded
motion and odometry would then disagree.

Current motor mapping:

| Rover side | Moteus CAN ID | Pi3Hat connection/bus | Command entry |
| --- | ---: | --- | --- |
| Left motor | `1` | `JC1` / bus `1` | `vel_cmd[1]` |
| Right motor | `2` | bus `2` | `vel_cmd[2]` |

The Moteus command limits are in `MoteusInterface.command()` in
`moteus_interface.py`:

```python
velocity_limit = 10.0
accel_limit = 6.5
```

Tune these conservatively for the motor, gearbox, power system, traction, and
vehicle mass. Note that Moteus velocity values are rotations per second, not
radians per second.

## Network configuration

Edit the telemetry destination near the bottom of `turtle.py`:

```python
PC_IP = "192.168.10.1"
PC_PORT = 5000
```

The rover listens for teleop commands on all interfaces at UDP port `5006`:

```python
teleop = TeleopSubscriber(port=5006)
```

Expected teleop packet:

```json
{"linear": 0.25, "angular": -0.15}
```

The telemetry packet sent to the PC includes wheel odometry position and
velocity, accelerometer data, gyro data, and IMU roll/pitch/yaw. Quaternion and
magnetometer fields are currently transmitted as zeros.

Allow the required UDP ports through any firewall and make sure the rover can
reach `PC_IP` before starting the motors.

## Run the rover

1. Raise the drive wheels and make the area safe.
2. Power the Pi3Hat and motor controllers.
3. Confirm motor IDs and CAN-bus mapping.
4. Start the remote teleop sender so it sends UDP JSON commands to the rover's
   IP address on port `5006`.
5. Run the active rover script:

```bash
cd /path/to/this/workspace
python3 turtle.py
```

Stop it with `Ctrl+C`. The `finally` block sends a Moteus stop/disarm command.
After stopping, verify physically that both motors are disabled.

For a simple network-only test from another computer, send a zero-speed packet:

```bash
printf '%s' '{"linear":0.0,"angular":0.0}' | nc -u -w1 ROVER_IP 5006
```

Replace `ROVER_IP` with the rover computer's IP address. Keep both values at zero
until the motor directions and emergency-stop procedure have been confirmed.

## Current limitations

- `agv.py` contains wheel-speed clamping code, but it is currently commented
  out. The configured `max_wheel_vel` therefore does not limit commands.
- Teleop values are not clamped before conversion. The sender should keep them
  within `-1.0` to `1.0`.
- `main.py` and `test.py` use older method signatures and should not be treated
  as production entry points without repair.
- Magnetometer acquisition and calibrated magnetometer heading are disabled.
- Quaternion and magnetometer telemetry fields are placeholders set to zero.
- Wheel odometry is open-loop with respect to slip and will accumulate position
  error over time.

## Troubleshooting

- **No motor response:** check power, Pi3Hat connection, Moteus IDs, CAN-bus
  mapping, and whether a controller fault needs to be cleared.
- **Rover drives backward:** verify the command signs for IDs 1 and 2.
- **Odometry moves backward while the rover moves forward:** apply the matching
  sign correction to the wheel-feedback conversion.
- **Incorrect travelled distance:** measure the loaded wheel radius and verify
  the gear-reduction value.
- **Incorrect turning angle:** measure wheel separation centre-to-centre and
  check for wheel slip.
- **Rover stops after about 0.5 seconds:** teleop packets are missing or too
  infrequent; this is the receiver's safety timeout.
- **No telemetry at the PC:** check `PC_IP`, UDP port `5000`, routing, and the
  firewall.

## Upload this README to GitHub

Copy this README into the cloned repository, review it, commit it, and push it to
the `lidar-navigation` branch. Commands are provided in the handoff message so
the source and destination paths can be confirmed before copying.
