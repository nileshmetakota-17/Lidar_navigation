# Rover ROS 2 Workspace — Version 2 Setup

This archive recreates the point-to-point rover workspace on Ubuntu 22.04 with
ROS 2 Humble. FAST-LIO and Isaac ROS are intentionally not included.

## 1. Install ROS 2 Humble

Install Ubuntu 22.04 64-bit, then follow the official ROS 2 Humble desktop
installation. Install the development tools and initialize rosdep:

```bash
sudo apt update
sudo apt install -y ros-humble-desktop ros-dev-tools
sudo rosdep init        # skip this command if already initialized
rosdep update
```

## 2. Clone the workspace from GitHub

Install Git and clone the `lidar-navigation` branch:

```bash
sudo apt update
sudo apt install -y git

cd ~
git clone --branch lidar-navigation \
  https://github.com/BhairavRobotics/GPS-and-Lidar-Fusion.git \
  rover_ros_ws_version2
cd ~/rover_ros_ws_version2
```

The Git repository intentionally contains no `build/`, `install/`, `log/`, or
`dist/` directories. These are machine-specific generated outputs and must be
created on the destination computer.

### 2.1 Pull later updates

Before pulling, check whether the local workspace contains uncommitted changes:

```bash
cd ~/rover_ros_ws_version2
git status
```

If the working tree is clean, download and apply the newest version of the
branch:

```bash
git switch lidar-navigation
git pull --rebase origin lidar-navigation
```

Reinstall dependencies and rebuild after pulling changes:

```bash
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
```

If `git status` reports local changes, commit or stash them before running
`git pull --rebase` to avoid mixing unfinished work with downloaded changes.

## 3. Install dependencies and build

### 3.1 Install Livox-SDK2

`livox_ros_driver2` requires Livox-SDK2, which is not installed by `rosdep`.
Install the SDK before building the ROS workspace:

```bash
sudo apt update
sudo apt install -y build-essential cmake git libapr1-dev

cd /tmp
git clone https://github.com/Livox-SDK/Livox-SDK2.git
cd Livox-SDK2
mkdir build
cd build
cmake ..
make -j"$(nproc)"
sudo make install
sudo ldconfig
```

Confirm that the shared library and headers were installed:

```bash
ls -l /usr/local/lib/liblivox_lidar_sdk_shared.so
ls -l /usr/local/include/livox_lidar_api.h
```

If the SDK repository already exists in `/tmp/Livox-SDK2`, remove it or use a
different clone directory before running the commands above.

### 3.2 Install ROS dependencies and build the workspace

```bash
cd ~/rover_ros_ws_version2
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y
colcon list
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
```

Expected packages:

```text
livox_ros_driver2
rover_control
rover_localization
rover_navigation
```

### 3.3 If the Livox package previously failed

The included CMake fix allows the normal workspace build above to work without
passing a separate `DISTRO_ROS` option. If `livox_ros_driver2` was already
configured before applying the fix, clear its CMake cache and rebuild it:

```bash
cd ~/rover_ros_ws_version2
source /opt/ros/humble/setup.bash
colcon build --symlink-install \
  --packages-select livox_ros_driver2 \
  --cmake-clean-cache \
  --event-handlers console_direct+
```

After it reports `Finished <<< livox_ros_driver2`, build all workspace packages
and load the completed overlay:

```bash
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
```

Lines containing `/usr/include/apr-1.0` and `apr-1` may be classified as stderr
by colcon, but they are harmless when the final summary reports that the package
finished successfully.

## 4. Configure the Livox network

The included configuration expects:

- computer/LiDAR interface: `192.168.10.4/24`
- Livox sensor: `192.168.10.147`
- rover controller: `192.168.10.2`
- ROS domain ID: `77`

Find and configure the wired connection (replace the connection name):

```bash
nmcli connection show
sudo nmcli connection modify "WIRED_CONNECTION_NAME" \
  ipv4.method manual ipv4.addresses 192.168.10.4/24 \
  ipv4.gateway "" ipv4.dns ""
sudo nmcli connection up "WIRED_CONNECTION_NAME"
ping -c 3 192.168.10.147
ping -c 3 192.168.10.2
```

For different addresses, update the Livox JSON files under
`src/livox_ros_driver2/config/` and the controller address in
`src/rover_control/rover_control/udp_bridge.py`.

## 5. Load the environment

### 5.1 Add the workspace to `.bashrc`

After the first successful `colcon build`, add this block to the end of
`~/.bashrc` on the new computer:

```bash
# Rover ROS 2 Humble workspace
if [ -f "$HOME/rover_ros_ws_version2/install/local_setup.bash" ]; then
  source "$HOME/rover_ros_ws_version2/scripts/rover_env.sh"
fi
```

You can append it with these commands:

```bash
cat >> ~/.bashrc <<'EOF'

# Rover ROS 2 Humble workspace
if [ -f "$HOME/rover_ros_ws_version2/install/local_setup.bash" ]; then
  source "$HOME/rover_ros_ws_version2/scripts/rover_env.sh"
fi
EOF
source ~/.bashrc
```

This automatically sources `/opt/ros/humble/setup.bash`, the workspace overlay,
and sets these required values in every new Bash terminal:

```bash
export ROS_DOMAIN_ID=77
export ROS_LOCALHOST_ONLY=0
```

Do not add `source ~/rover_ros_ws_version2/install/setup.bash` separately; the
helper already loads it and avoids duplicate or stale environment entries. If
you extract the workspace under another name or location, change the two paths
in the `.bashrc` block accordingly.

### 5.2 Load it manually

If you do not want to edit `.bashrc`, run this in every new terminal:

```bash
cd ~/rover_ros_ws_version2
source scripts/rover_env.sh
```

The script discovers its workspace location, sources ROS Humble and the local
overlay, and exports `ROS_DOMAIN_ID=77`.

## 6. Run point-to-point navigation

Use three sourced terminals:

```bash
# Terminal 1
./scripts/start_livox.sh

# Terminal 2
ros2 run rover_control udp_bridge

# Terminal 3
ros2 launch rover_navigation nav2_launch.py
```

In RViz, set the initial pose with **2D Pose Estimate**, then send a destination
with **Nav2 Goal**.

## 7. Verify

```bash
ros2 pkg prefix livox_ros_driver2
ros2 pkg prefix rover_control
ros2 pkg prefix rover_localization
ros2 pkg prefix rover_navigation
ros2 topic hz /livox/lidar
ros2 topic hz /livox/imu
```

If generated files contain an old workspace path, remove only generated
outputs and rebuild:

```bash
cd ~/rover_ros_ws_version2
rm -rf build install log
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src --rosdistro humble -r -y
colcon build --symlink-install --event-handlers console_direct+
source install/setup.bash
```

## 8. Create a new portable ZIP

On the source computer, install `zip` once and run the archive utility:

```bash
cd ~/rover_ros_ws_version2
sudo apt install -y zip
./scripts/create_portable_zip.sh
```

The result is `dist/rover_ros_ws_version2.zip`. The utility includes the source,
configuration, maps, scripts, and documentation, while excluding generated
`build/`, `install/`, and `log/` trees, Git/Codex metadata, caches, virtual
environments, FAST-LIO, and Isaac ROS workspaces. It also prints a SHA-256
checksum that can be checked after copying:

```bash
sha256sum rover_ros_ws_version2.zip
```
