# Rover ROS 2 Command Cheat Sheet

A compact reference for building, launching, testing, and debugging the rover ROS 2 workspace.

---

## 1. Workspace Navigation

```bash
cd ~/rover_ros_ws
cd ~/rover_ros_ws/src
ls ~/rover_ros_ws/src
```

Show the workspace tree:

```bash
find ~/rover_ros_ws/src -maxdepth 2 -type d | sort
```

---

## 2. Source the ROS 2 Environment

Run these commands in every new terminal:

```bash
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/setup.bash
```

A convenient one-line version:

```bash
source /opt/ros/humble/setup.bash && source ~/rover_ros_ws/install/setup.bash
```

Add them permanently to Bash:

```bash
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source ~/rover_ros_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

---

## 3. Build the Workspace

Build all packages:

```bash
cd ~/rover_ros_ws
colcon build --symlink-install
source install/setup.bash
```

Build selected packages:

```bash
cd ~/rover_ros_ws

colcon build \
  --symlink-install \
  --packages-select rover_control

colcon build \
  --symlink-install \
  --packages-select rover_localization

source install/setup.bash
```

Build multiple selected packages:

```bash
colcon build \
  --symlink-install \
  --packages-select rover_control rover_localization
```

Build a package and its dependencies:

```bash
colcon build \
  --symlink-install \
  --packages-up-to rover_localization
```

Show detailed build output:

```bash
colcon build \
  --symlink-install \
  --event-handlers console_direct+
```

Clean the workspace before rebuilding:

```bash
cd ~/rover_ros_ws
rm -rf build install log
colcon build --symlink-install
source install/setup.bash
```

---

## 4. Package Checks

List rover and localization-related packages:

```bash
ros2 pkg list | grep -E "rover_|livox_ros_driver2|fast_lio"
```

List package executables:

```bash
ros2 pkg executables rover_control
ros2 pkg executables rover_localization
```

Find a package installation prefix:

```bash
ros2 pkg prefix rover_control
ros2 pkg prefix rover_localization
```

Inspect package metadata:

```bash
ros2 pkg xml rover_control
ros2 pkg xml rover_localization
```

---

## 5. Recommended Startup Order

Use a separate terminal for each major process.

### Terminal 1 — UDP Bridge

```bash
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/setup.bash

ros2 run rover_control udp_bridge
```

### Terminal 2 — EKF Localization

```bash
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/setup.bash

ros2 launch rover_localization ekf.launch.py
```

### Terminal 3 — Rover Command

Choose one command:

```bash
ros2 run rover_control keyboard_teleop \
  --ros-args \
  -p odometry_topic:=/odometry/filtered
```

```bash
ros2 run rover_control move_x 1.0
```

```bash
ros2 run rover_control rotate 90
```

```bash
ros2 run rover_control spin
```

### Joystick control

```bash
ros2 launch rover_control joy.launch.py
```

Use a gentler slowdown:

```bash
ros2 launch rover_control joy.launch.py linear_kp:=2.5 angular_kp:=3.0
```

### Terminal 4 — Monitoring

```bash
ros2 run rover_localization print_filtered
```

or:

```bash
ros2 run rover_localization print_position
```

or:

```bash
ros2 run rover_localization print_imu
```

---

## 6. Rover Control Commands

Start the UDP bridge:

```bash
ros2 run rover_control udp_bridge
```

Start keyboard teleoperation:

```bash
ros2 run rover_control keyboard_teleop \
  --ros-args \
  -p odometry_topic:=/odometry/filtered
```

Move forward by 1 metre:

```bash
ros2 run rover_control move_x 1.0
```

Move backward by 1 metre:

```bash
ros2 run rover_control move_x -1.0
```

Rotate counterclockwise by 90 degrees:

```bash
ros2 run rover_control rotate 90
```

Rotate clockwise by 90 degrees:

```bash
ros2 run rover_control rotate -90
```

Start continuous spinning:

```bash
ros2 run rover_control spin
```

Pass ROS parameters:

```bash
ros2 run rover_control move_x 1.0 \
  --ros-args \
  -p odometry_topic:=/odometry/filtered
```

---

## 7. Localization Commands

Start the EKF:

```bash
ros2 launch rover_localization ekf.launch.py
```

Convert filtered odometry into a path:

```bash
ros2 run rover_localization odom_to_path
```

Print filtered odometry:

```bash
ros2 run rover_localization print_filtered
```

Print rover position:

```bash
ros2 run rover_localization print_position
```

Print IMU values:

```bash
ros2 run rover_localization print_imu
```

Check whether the EKF node is running:

```bash
ros2 node list | grep ekf
```

Check EKF parameters:

```bash
ros2 param list /ekf_filter_node
```

---

## 8. Livox MID-360

### Known working network and ROS settings

For the current Wi-Fi setup:

```text
Host IP:       192.168.10.4
LiDAR IP:      192.168.10.147
ROS domain ID: 77
```

Use the MID360S launch file when Livox Viewer identifies the sensor as a
MID360S:

```bash
export ROS_DOMAIN_ID=77
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/local_setup.bash
ros2 launch livox_ros_driver2 msg_MID360s_launch.py
```

For a regular MID-360, use:

```bash
ros2 launch livox_ros_driver2 msg_MID360_launch.py
```

Check Livox topics:

```bash
ros2 topic list | grep -i livox
```

Check LiDAR rate:

```bash
ros2 topic hz /livox/lidar
```

Check Livox IMU rate:

```bash
ros2 topic hz /livox/imu
```

Echo one LiDAR message:

```bash
ros2 topic echo /livox/lidar --once
```

Echo one Livox IMU message:

```bash
ros2 topic echo /livox/imu --once
```

### Build only the Livox driver

Build from a clean ROS environment so an older workspace overlay is not used:

```bash
cd ~/rover_ros_ws
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH
source /opt/ros/humble/setup.bash

colcon build \
  --packages-select livox_ros_driver2 \
  --symlink-install \
  --cmake-clean-cache \
  --cmake-args -DROS_EDITION=ROS2 -DDISTRO_ROS=humble
```

Source and verify the rebuilt package:

```bash
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/local_setup.bash
ros2 pkg prefix livox_ros_driver2
```

Expected prefix:

```text
/home/nilesh/rover_ros_ws/install/livox_ros_driver2
```

### Troubleshooting: driver initializes but publishes no topic

Observed symptoms included:

```text
Init lds lidar success!
GetFreeIndex key:livox_lidar_2466949312.
WARNING: topic [/livox/lidar] does not appear to be published yet
```

`GetFreeIndex` only means the configured LiDAR IP was loaded. It does not mean
the LiDAR handshake completed or point data started.

The issues found were:

1. The host address in the JSON did not initially match the active Wi-Fi
   address. The correct host address is `192.168.10.4`, and the LiDAR address is
   `192.168.10.147`.
2. Different terminals used different ROS domain IDs. Use
   `ROS_DOMAIN_ID=77` everywhere. Do not use `7777`; Fast DDS domain IDs must
   not exceed 232.
3. An older overlay at `~/Pocs/ws_livox` was selected instead of the rover
   workspace. Its launch/config files caused the wrong configuration to load.
4. MID360 and MID360S have separate launch and configuration files. Use
   `msg_MID360s_launch.py` for a sensor reported as MID360S by Livox Viewer.
5. A previous driver process can retain UDP port 56000 and cause `bind failed`.
   Stop the previous launch with `Ctrl+C` before starting another one.

Reset an old overlay and confirm package resolution:

```bash
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/local_setup.bash
export ROS_DOMAIN_ID=77

ros2 pkg prefix livox_ros_driver2
```

The launch log must load its configuration from `~/rover_ros_ws`, not from
`~/Pocs/ws_livox`.

Verify the active network route and broadcast discovery:

```bash
ip route get 192.168.10.147
sudo tcpdump -ni wlp108s0 'udp port 56000'
```

The route should use source address `192.168.10.4`. Discovery is working when
UDP port 56000 packets are visible in both directions between `192.168.10.4`
and `192.168.10.147`.

After launching, verify ROS discovery and data:

```bash
export ROS_DOMAIN_ID=77
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/local_setup.bash

ros2 daemon stop
ros2 daemon start
ros2 node list
ros2 topic list -t | grep livox
ros2 topic hz /livox/lidar
```

---

## 9. FAST-LIO

### Helper scripts

Load the clean rover ROS environment in the current terminal:

```bash
source ~/rover_ros_ws/scripts/rover_env.sh
```

Start only the Livox MID360S driver:

```bash
~/rover_ros_ws/scripts/start_livox.sh
```

Start only FAST-LIO after verifying that real LiDAR and IMU messages are
arriving:

```bash
~/rover_ros_ws/scripts/start_fastlio.sh
```

Start the Livox driver and FAST-LIO together:

```bash
~/rover_ros_ws/scripts/start_livox_fastlio.sh
```

The combined script waits up to 30 seconds for a real `/livox/lidar` message
before starting FAST-LIO. Press `Ctrl+C` to stop both processes. Completely
close Livox Viewer before using the combined script.

### Rebuild FAST-LIO if the package is missing

If the launcher reports:

```text
Package 'fast_lio' not found
```

the `install/fast_lio` output is missing, often because the workspace install
directory was cleaned and only selected packages were rebuilt. Rebuild it
against the installed Livox messages:

```bash
cd ~/rover_ros_ws
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH
source /opt/ros/humble/setup.bash
source install/livox_ros_driver2/share/livox_ros_driver2/local_setup.bash

colcon build \
  --packages-select fast_lio \
  --symlink-install \
  --cmake-clean-cache
```

Verify and reload the environment:

```bash
source ~/rover_ros_ws/scripts/rover_env.sh
ros2 pkg prefix fast_lio
ros2 pkg executables fast_lio
```

Expected prefix and executable:

```text
/home/nilesh/rover_ros_ws/install/fast_lio
fast_lio fastlio_mapping
```

Start FAST-LIO without RViz:

```bash
ros2 launch fast_lio mapping.launch.py \
  config_file:=mid360.yaml \
  rviz:=false
```

Start FAST-LIO with RViz:

```bash
ros2 launch fast_lio mapping.launch.py \
  config_file:=mid360.yaml \
  rviz:=true
```

Check FAST-LIO nodes:

```bash
ros2 node list | grep -i lio
```

Check FAST-LIO odometry:

```bash
ros2 topic hz /Odometry
ros2 topic echo /Odometry --once
```

### Start SLAM Toolbox with RViz

The `rover_navigation` SLAM launch converts FAST-LIO's
`/cloud_registered` point cloud into `/scan`, starts SLAM Toolbox, and opens
RViz automatically:

```bash
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/local_setup.bash
export ROS_DOMAIN_ID=77

ros2 launch rover_navigation slam_launch.py
```

The RViz configuration displays:

```text
Fixed frame:          map
Occupancy grid:       /map
Converted laser scan: /scan
FAST-LIO point cloud: /cloud_registered
Transforms:           /tf
```

Start SLAM without RViz:

```bash
ros2 launch rover_navigation slam_launch.py rviz:=false
```

Use a different RViz configuration:

```bash
ros2 launch rover_navigation slam_launch.py \
  rviz_config:=/absolute/path/to/config.rviz
```

Verify the converted scan:

```bash
ros2 topic list -t | grep -E '^/scan '
ros2 topic info /scan -v
ros2 topic hz /scan
ros2 topic echo /scan --once --field range_min
```

Expected type and minimum range:

```text
/scan    sensor_msgs/msg/LaserScan
range_min: approximately 0.3 m
```

Only one `pointcloud_to_laserscan` publisher should normally appear in
`ros2 topic info /scan -v`. If two publishers appear, stop the older SLAM
launch with `Ctrl+C` before starting another one.

The matching SLAM Toolbox setting is stored in
`rover_navigation/config/slam_toolbox_params.yaml`:

```yaml
min_laser_range: 0.3
```

The converter is configured for a bounded 360-degree scan with 720 rays
(`angle_increment: 0.00872665`) and reliable `/scan` QoS. If SLAM Toolbox exits
with code `-9`, check for an out-of-memory kill:

```bash
journalctl -k --since "10 minutes ago" | grep -Ei 'oom|killed process'
free -h
```

An exit code of `-9` accompanied by `Out of memory: Killed process ...
sync_slam_toolb` means the Linux kernel terminated SLAM Toolbox; it is not a
normal ROS shutdown.

Rebuild the navigation package after changing its launch or configuration
files:

```bash
cd ~/rover_ros_ws
unset AMENT_PREFIX_PATH COLCON_PREFIX_PATH CMAKE_PREFIX_PATH
source /opt/ros/humble/setup.bash
colcon build --packages-select rover_navigation --symlink-install
```

### Start Nav2 on a saved map

Start Livox and FAST-LIO first. Confirm that FAST-LIO odometry is stable near
its startup origin, then launch Nav2:

```bash
source ~/rover_ros_ws/scripts/rover_env.sh
ros2 launch rover_navigation nav2_launch.py
```

The direct launcher starts the point-cloud converter, map server, AMCL,
planner, controller, behavior server, BT navigator, waypoint follower,
velocity smoother, lifecycle manager, and RViz. Livox, FAST-LIO, and the UDP
bridge must already be running.

After RViz opens, use **2D Pose Estimate** to place the rover at its actual
position in the saved map. Only send a navigation goal after localization is
correct.

Useful overrides:

```bash
ros2 launch rover_navigation nav2_launch.py \
  map:=/home/nilesh/rover_ros_ws/src/rover_navigation/maps/ofc_map.yaml \
  rviz:=true
```

Run without RViz:

```bash
ros2 launch rover_navigation nav2_launch.py rviz:=false
```

If Nav2 reports that the robot or sensor origin is outside the global costmap,
the `map -> camera_init -> body` pose lies outside the saved occupancy-map
bounds. Correct the RViz initial pose or restart/fix diverged FAST-LIO; changing
costmap width does not repair a wrong robot pose.

If a message filter drops old `body` messages, check freshness and duplicate
scan publishers:

```bash
ros2 topic echo /scan --once --field header
ros2 topic info /scan -v
ros2 topic echo /Odometry --once --field pose.pose.position
```

### Nav2 TF and command-source checks

This rover currently exposes two independent TF trees:

```text
Nav2 / FAST-LIO:  map -> camera_init -> body
Wheel / EKF:      odom -> base_link -> imu_link
```

Nav2 is configured to track `body` through the FAST-LIO tree. A transform such
as `map -> base_link` will not exist while these trees remain intentionally
separate. Check the transforms Nav2 actually uses:

```bash
ros2 run tf2_ros tf2_echo map body
ros2 run tf2_ros tf2_echo camera_init body
```

AMCL does not publish `map -> camera_init` until it receives an initial pose.
Use RViz **2D Pose Estimate**, then verify:

```bash
ros2 run tf2_ros tf2_echo map camera_init
```

Nav2's controller publishes internally to `/cmd_vel_nav`. The velocity
smoother publishes the final command to `/cmd_vel`, and `udp_bridge` subscribes
to `/cmd_vel`:

```text
controller_server -> /cmd_vel_nav -> velocity_smoother -> /cmd_vel -> udp_bridge
```

Do not run joystick or keyboard teleoperation at the same time as Nav2. Check
for competing command sources:

```bash
ros2 topic info /cmd_vel -v
ros2 node list | grep -E 'joy|keyboard_teleop'
```

The Nav2 launcher now rejects startup when `/sony_joy_rover_teleop` or
`/keyboard_teleop` is active. Stop the teleoperation launch with `Ctrl+C`
before starting Nav2.

If Nav2 reports `Reached the goal` immediately, verify that the goal is more
than the configured `0.20 m` position tolerance from the current `map -> body`
pose and that the RViz initial pose is correct:

```bash
ros2 run tf2_ros tf2_echo map body
ros2 topic echo /cmd_vel
```

Repeated `RTPS_TRANSPORT_SHM` lock errors together with delayed TF data indicate
stale Fast DDS shared-memory state. Stop all ROS processes or reboot before a
clean navigation run.

Recommended clean startup order:

```text
1. ros2 run rover_control udp_bridge
2. ~/rover_ros_ws/scripts/start_livox_fastlio.sh
3. ros2 launch rover_navigation nav2_launch.py
4. Set RViz 2D Pose Estimate
5. Send a navigation goal
```

### Save the FAST-LIO map as PCD

The MID360 configuration has PCD saving enabled and writes the map to:

```text
~/rover_ros_ws/src/maps/my_map.pcd
```

While FAST-LIO mapping is running, save the current map:

```bash
mkdir -p ~/rover_ros_ws/src/maps
ros2 service call /map_save std_srvs/srv/Trigger "{}"
```

Confirm that the file was created:

```bash
ls -lh ~/rover_ros_ws/src/maps/my_map.pcd
```

Open the saved point cloud:

```bash
pcl_viewer ~/rover_ros_ws/src/maps/my_map.pcd
```

If the service reports `Map save disabled`, verify these settings in
`FAST_LIO_ROS2/config/mid360.yaml`:

```yaml
map_file_path: "/home/nilesh/rover_ros_ws/src/maps/my_map.pcd"
pcd_save:
    pcd_save_en: true
```

---

## 10. ROS Graph Inspection

List active nodes:

```bash
ros2 node list
```

Inspect a node:

```bash
ros2 node info /udp_bridge
ros2 node info /ekf_filter_node
```

List all topics:

```bash
ros2 topic list
```

List topics with message types:

```bash
ros2 topic list -t
```

Inspect important topics:

```bash
ros2 topic info /odom -v
ros2 topic info /imu/data -v
ros2 topic info /odometry/filtered -v
```

Generate an interactive ROS graph:

```bash
rqt_graph
```

---

## 11. Important Topic Types

Check a topic type:

```bash
ros2 topic type /odom
ros2 topic type /imu/data
ros2 topic type /odometry/filtered
```

Expected types:

```text
/odom                 nav_msgs/msg/Odometry
/imu/data             sensor_msgs/msg/Imu
/odometry/filtered    nav_msgs/msg/Odometry
/cmd_vel              geometry_msgs/msg/Twist
```

---

## 12. Topic Rates

Raw wheel odometry:

```bash
ros2 topic hz /odom
```

Raw IMU:

```bash
ros2 topic hz /imu/data
```

Filtered odometry:

```bash
ros2 topic hz /odometry/filtered
```

Livox LiDAR:

```bash
ros2 topic hz /livox/lidar
```

Livox IMU:

```bash
ros2 topic hz /livox/imu
```

FAST-LIO odometry:

```bash
ros2 topic hz /Odometry
```

Command velocity:

```bash
ros2 topic hz /cmd_vel
```

---

## 13. Echo Topic Data

Echo one raw odometry message:

```bash
ros2 topic echo /odom --once
```

Echo one IMU message:

```bash
ros2 topic echo /imu/data --once
```

Echo one filtered odometry message:

```bash
ros2 topic echo /odometry/filtered --once
```

Echo selected fields:

```bash
ros2 topic echo /odom --field pose.pose.position
```

```bash
ros2 topic echo /imu/data --field angular_velocity
```

```bash
ros2 topic echo /odometry/filtered --field pose.pose.position
```

```bash
ros2 topic echo /odometry/filtered --field twist.twist
```

---

## 14. Publish Test Commands

Stop the rover:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

Move forward slowly:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"
```

Rotate counterclockwise slowly:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.3}}"
```

Rotate clockwise slowly:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: -0.3}}"
```

Press `Ctrl+C` to stop continuous publishing.

---

## 15. TF Checks

Check the IMU mounting transform:

```bash
ros2 run tf2_ros tf2_echo base_link imu_link
```

Check the fused odometry transform:

```bash
ros2 run tf2_ros tf2_echo odom base_link
```

Check map to odom:

```bash
ros2 run tf2_ros tf2_echo map odom
```

Create a TF tree report:

```bash
ros2 run tf2_tools view_frames
```

The command generates a file such as:

```text
frames.pdf
```

Monitor all transforms:

```bash
ros2 topic echo /tf
```

Monitor static transforms:

```bash
ros2 topic echo /tf_static
```

Check for multiple `/tf` publishers:

```bash
ros2 topic info /tf -v
```

Only one node should normally publish the same `odom -> base_link` transform.

---

## 16. EKF Diagnostics

View diagnostics:

```bash
ros2 topic echo /diagnostics
```

Check EKF sensor topics:

```bash
ros2 param get /ekf_filter_node odom0
ros2 param get /ekf_filter_node imu0
```

Check EKF frames:

```bash
ros2 param get /ekf_filter_node map_frame
ros2 param get /ekf_filter_node odom_frame
ros2 param get /ekf_filter_node base_link_frame
ros2 param get /ekf_filter_node world_frame
```

Check EKF frequency and TF publishing:

```bash
ros2 param get /ekf_filter_node frequency
ros2 param get /ekf_filter_node publish_tf
ros2 param get /ekf_filter_node two_d_mode
```

Dump all EKF parameters:

```bash
ros2 param dump /ekf_filter_node
```

---

## 17. Check Odometry and IMU Frames

Raw odometry frames:

```bash
ros2 topic echo /odom --once | grep -E "frame_id|child_frame_id"
```

IMU frame:

```bash
ros2 topic echo /imu/data --once | grep frame_id
```

Filtered odometry frames:

```bash
ros2 topic echo /odometry/filtered --once | grep -E "frame_id|child_frame_id"
```

Typical frame setup:

```text
Odometry header.frame_id:       odom
Odometry child_frame_id:        base_link
IMU header.frame_id:            imu_link
Filtered odometry frame_id:     odom
Filtered child_frame_id:        base_link
```

---

## 18. Check Covariance Values

Raw odometry:

```bash
ros2 topic echo /odom --once
```

Inspect:

```text
pose.covariance
twist.covariance
```

IMU:

```bash
ros2 topic echo /imu/data --once
```

Inspect:

```text
orientation_covariance
angular_velocity_covariance
linear_acceleration_covariance
```

Filtered odometry:

```bash
ros2 topic echo /odometry/filtered --once
```

Avoid leaving all covariance values at zero unless the measurement is genuinely perfect.

---

## 19. Useful Package Locations

```bash
cd ~/rover_ros_ws/src/rover_control
cd ~/rover_ros_ws/src/rover_localization
cd ~/rover_ros_ws/src/rover_navigation
cd ~/rover_ros_ws/src/livox_ros_driver2
cd ~/rover_ros_ws/src/FAST_LIO_ROS2
```

List package files:

```bash
find ~/rover_ros_ws/src/rover_control -maxdepth 3 -type f | sort
find ~/rover_ros_ws/src/rover_localization -maxdepth 3 -type f | sort
```

---

## 20. Locate Launch and Configuration Files

Find launch files:

```bash
find ~/rover_ros_ws/src -type f \
  \( -name "*.launch.py" -o -name "*.launch.xml" -o -name "*.launch.yaml" \) \
  | sort
```

Find YAML configuration files:

```bash
find ~/rover_ros_ws/src -type f \
  \( -name "*.yaml" -o -name "*.yml" \) \
  | sort
```

Search for odometry or IMU topic names:

```bash
grep -RniE "/odom|/imu/data|/odometry/filtered" \
  ~/rover_ros_ws/src
```

Search for TF publishers:

```bash
grep -RniE "publish_tf|TransformBroadcaster|odom.*base_link" \
  ~/rover_ros_ws/src
```

---

## 21. Launch File Checks

Show launch arguments:

```bash
ros2 launch rover_localization ekf.launch.py --show-args
```

Check whether a launch file is installed:

```bash
find ~/rover_ros_ws/install/rover_localization \
  -type f \
  -name "*.launch.py"
```

Run a launch file with debug logs:

```bash
ros2 launch rover_localization ekf.launch.py \
  --ros-args \
  --log-level debug
```

---

## 22. Parameter Overrides

Override an odometry topic:

```bash
ros2 run rover_localization odom_to_path \
  --ros-args \
  -p odometry_topic:=/odometry/filtered
```

Override a path topic:

```bash
ros2 run rover_localization odom_to_path \
  --ros-args \
  -p path_topic:=/model/rover/path_fused
```

Override both:

```bash
ros2 run rover_localization odom_to_path \
  --ros-args \
  -p odometry_topic:=/odometry/filtered \
  -p path_topic:=/model/rover/path_fused
```

---

## 23. Log Files

ROS 2 logs are stored under:

```bash
ls ~/.ros/log
```

Show the newest log directory:

```bash
ls -td ~/.ros/log/* | head
```

Run a node with debug-level logs:

```bash
ros2 run rover_control udp_bridge \
  --ros-args \
  --log-level debug
```

---

## 24. Network Checks for the UDP Bridge

Show local IP addresses:

```bash
ip addr
```

Check connectivity to the Raspberry Pi:

```bash
ping 192.168.10.2
```

Check UDP sockets:

```bash
ss -lunp
```

Look for UDP port `5000`:

```bash
ss -lunp | grep 5000
```

Look for UDP port `5006`:

```bash
ss -lunp | grep 5006
```

Capture UDP packets:

```bash
sudo tcpdump -i any udp port 5000
```

Capture both rover UDP ports:

```bash
sudo tcpdump -i any \
  "udp port 5000 or udp port 5006"
```

---

## 25. Common Troubleshooting

### Package not found

```bash
source /opt/ros/humble/setup.bash
source ~/rover_ros_ws/install/setup.bash
ros2 pkg list | grep rover
```

If still missing:

```bash
cd ~/rover_ros_ws
colcon build --symlink-install
source install/setup.bash
```

### Executable not found

```bash
ros2 pkg executables rover_control
ros2 pkg executables rover_localization
```

For Python packages, check the `console_scripts` entries in `setup.py`.

### No `/odom` data

```bash
ros2 topic info /odom -v
ros2 topic hz /odom
ros2 topic echo /odom --once
```

Check whether `udp_bridge` is running and receiving packets.

### No `/imu/data` data

```bash
ros2 topic info /imu/data -v
ros2 topic hz /imu/data
ros2 topic echo /imu/data --once
```

### No `/odometry/filtered` data

```bash
ros2 node list | grep ekf
ros2 topic info /odometry/filtered -v
ros2 topic hz /odometry/filtered
ros2 topic echo /diagnostics
```

Check the EKF sensor topic parameters:

```bash
ros2 param get /ekf_filter_node odom0
ros2 param get /ekf_filter_node imu0
```

### Transform not available

```bash
ros2 run tf2_ros tf2_echo base_link imu_link
ros2 run tf2_ros tf2_echo odom base_link
ros2 topic info /tf -v
```

### Command is published but rover does not move

```bash
ros2 topic info /cmd_vel -v
ros2 topic echo /cmd_vel
ros2 topic hz /cmd_vel
```

Check that `udp_bridge` subscribes to `/cmd_vel`.

---

## 26. Stop a Running Node

Press:

```text
Ctrl+C
```

in the terminal running the node.

Send an explicit zero-velocity command if needed:

```bash
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.0}}"
```

List processes containing ROS commands:

```bash
ps aux | grep -E "ros2|udp_bridge|ekf|fast_lio|livox"
```

Stop a process only when normal `Ctrl+C` shutdown is unavailable:

```bash
pkill -f udp_bridge
```

---

## 27. Quick Full-System Sequence

### Build

```bash
cd ~/rover_ros_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### Start UDP bridge

```bash
ros2 run rover_control udp_bridge
```

### Start EKF

```bash
ros2 launch rover_localization ekf.launch.py
```

### Confirm sensor and fusion rates

```bash
ros2 topic hz /odom
ros2 topic hz /imu/data
ros2 topic hz /odometry/filtered
```

### Check TF

```bash
ros2 run tf2_ros tf2_echo base_link imu_link
ros2 run tf2_ros tf2_echo odom base_link
```

### Command the rover

```bash
ros2 run rover_control move_x 1.0
```

or:

```bash
ros2 run rover_control rotate 90
```

### Monitor filtered pose

```bash
ros2 run rover_localization print_filtered
```

---

## 28. Quick Reference

| Task | Command |
|---|---|
| Build workspace | `colcon build --symlink-install` |
| Source workspace | `source ~/rover_ros_ws/install/setup.bash` |
| Start UDP bridge | `ros2 run rover_control udp_bridge` |
| Start EKF | `ros2 launch rover_localization ekf.launch.py` |
| Move forward 1 m | `ros2 run rover_control move_x 1.0` |
| Move backward 1 m | `ros2 run rover_control move_x -1.0` |
| Rotate left 90° | `ros2 run rover_control rotate 90` |
| Rotate right 90° | `ros2 run rover_control rotate -90` |
| Show nodes | `ros2 node list` |
| Show topics | `ros2 topic list -t` |
| Check raw odometry | `ros2 topic echo /odom --once` |
| Check raw IMU | `ros2 topic echo /imu/data --once` |
| Check fused odometry | `ros2 topic echo /odometry/filtered --once` |
| Check fused rate | `ros2 topic hz /odometry/filtered` |
| Check odom TF | `ros2 run tf2_ros tf2_echo odom base_link` |
| Stop rover | Publish zero `/cmd_vel` or press `Ctrl+C` |

---

## Notes

### Nav2 says `map` does not exist or drops `body` messages

FAST-LIO publishes the `camera_init -> body` TF chain. AMCL must therefore use
`odom_frame_id: camera_init` and `base_frame_id: body`. Check the parameters
actually loaded by the running node:

```bash
ros2 param get /amcl odom_frame_id
ros2 param get /amcl base_frame_id
```

If these print `odom` and `base_link`, Nav2 is using an old installed config.
Stop Nav2, rebuild and re-source it, then launch it again:

```bash
cd ~/rover_ros_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select rover_navigation --symlink-install
source install/local_setup.bash
export ROS_DOMAIN_ID=77
ros2 launch rover_navigation nav2_launch.py
```

After relaunch, verify `camera_init` and `body`, set the initial pose with RViz
**2D Pose Estimate**, and confirm the global transform:

```bash
ros2 param get /amcl odom_frame_id
ros2 param get /amcl base_frame_id
ros2 run tf2_ros tf2_echo map camera_init
```

- A printed `/initialpose` message or "matching subscription" only proves that
  the message was delivered. AMCL will not publish `map -> camera_init` when it
  was started with the incompatible `odom -> base_link` frame configuration.

- Source both ROS 2 Humble and the workspace in every new terminal.
- Rebuild and re-source after changing Python entry points, launch files, package metadata, or installed configuration files.
- Use `/odometry/filtered` for motion control after the EKF is verified.
- Only one node should publish the same `odom -> base_link` transform.
- Test low movement and rotation speeds before operating at higher speeds.
- Verify that the rover is raised safely or has enough clear space before publishing test velocity commands.
