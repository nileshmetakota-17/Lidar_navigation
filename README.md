# LiDAR Navigation

Version 2 of the ROS 2 Humble rover workspace for point-to-point navigation.
It combines wheel and IMU odometry with point-cloud data from a Livox
MID-360/MID-360S LiDAR. The workspace contains rover control, localization,
navigation, mapping, and Livox driver packages.

FAST-LIO and Isaac ROS are intentionally not included in this version.

## Documentation

- **[Setup guide](SETUP_VERSION2.md):** system requirements, dependency
  installation, Livox-SDK2 setup, network configuration, workspace build,
  startup, verification, and troubleshooting.
- **[Command reference](COMMANDS.md):** commonly used build, launch, control,
  localization, navigation, monitoring, and debugging commands.
- **[Portable archive manifest](VERSION2_MANIFEST.md):** files included in and
  excluded from the portable workspace archive.

## Contents

| Package | Purpose |
|---|---|
| `rover_control` | UDP chassis bridge, keyboard/joystick teleop, motion commands |
| `rover_localization` | `robot_localization` EKF and diagnostic/visualization nodes |
| `rover_navigation` | Nav2, SLAM Toolbox, point-cloud conversion, RViz, and maps |
| `livox_ros_driver2` | Livox ROS 2 device driver and messages |

Generated `build/`, `install/`, `log/`, and `dist/` directories are ignored by
Git. Rebuild the workspace on each destination system rather than copying
machine-specific build output.

## Quick start on another computer

Use **Ubuntu 22.04 (Jammy), 64-bit, with ROS 2 Humble Desktop**. Clone the
repository and follow the complete [setup guide](SETUP_VERSION2.md):

```bash
git clone https://github.com/BhairavRobotics/GPS-and-Lidar-Fusion.git \
  GPS-and-Lidar-Fusion-lidar-navigation
cd GPS-and-Lidar-Fusion-lidar-navigation
git switch lidar-navigation
```

Install the documented dependencies, then build:

```bash
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
```

After setup and build, every new terminal can load the environment with:

```bash
cd /path/to/GPS-and-Lidar-Fusion-lidar-navigation
source scripts/rover_env.sh
```

Start the raw Livox PointCloud2 driver:

```bash
./scripts/start_livox.sh
```

For point-to-point navigation on an existing map, start these in separate
sourced terminals:

```bash
ros2 run rover_control udp_bridge
ros2 launch rover_navigation nav2_launch.py
```

For more launch, control, inspection, and debugging examples, use the
[command cheat sheet](COMMANDS.md).

## Hardware/network values to check

The current configuration expects:

- computer/LiDAR-interface IP: `192.168.10.4`
- Livox LiDAR IP: `192.168.10.147`
- rover controller/Raspberry Pi IP: `192.168.10.2`
- ROS domain ID: `77`

If the new system uses different addresses, update:

- `src/livox_ros_driver2/config/MID360_config.json`
- `src/livox_ros_driver2/config/MID360s_config.json`
- `scripts/start_livox.sh`
- `src/rover_control/rover_control/udp_bridge.py`

## Important notes

- Do not copy or source an `install/` directory built on another computer;
  colcon-generated files contain absolute paths.
- Only one node should publish `odom -> base_link`.
- Close Livox Viewer before starting the ROS driver because they can compete for
  the same UDP ports.
- The current chassis IMU has no valid orientation quaternion; the EKF should
  not fuse its yaw orientation.

## V2 data flow

```text
Livox /livox/lidar (raw PointCloud2)
             -> pointcloud_to_laserscan -> /scan
             -> AMCL + Nav2 costmaps

chassis /odom + Livox /livox/imu
             -> robot_localization EKF -> /odometry/filtered + odom->base_link

saved map + AMCL + filtered odometry
             -> Nav2 point-to-point goal -> /cmd_vel_nav
             -> velocity smoother -> twist_mux -> /cmd_vel -> UDP rover bridge
```

The supplied map defaults to `src/rover_navigation/maps/ofc_map2.yaml`. In RViz,
set the initial pose with **2D Pose Estimate**, then send a destination with
**Nav2 Goal**.

## Results

### Test demo

<video controls preload="metadata" width="100%">
  <source src="test%20videos/test-demo.mp4" type="video/mp4">
  Your browser does not support embedded video. Open the
  <a href="test%20videos/test-demo.mp4">test demo video</a> instead.
</video>

[Play the test demo video](test%20videos/test-demo.mp4) ·
[Recording details and local playback instructions](test%20videos/README.md)
