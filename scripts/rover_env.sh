#!/usr/bin/env bash
# Source this file before running rover ROS 2 commands.
# It works regardless of where the workspace was extracted.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROVER_WS="$(cd -- "${SCRIPT_DIR}/.." && pwd)"

unset AMENT_PREFIX_PATH
unset COLCON_PREFIX_PATH
unset CMAKE_PREFIX_PATH

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  echo "ERROR: ROS 2 Humble is not installed at /opt/ros/humble." >&2
  return 1 2>/dev/null || exit 1
fi

if [[ ! -f "${ROVER_WS}/install/local_setup.bash" ]]; then
  echo "ERROR: workspace is not built. Run: cd ${ROVER_WS} && colcon build --symlink-install" >&2
  return 1 2>/dev/null || exit 1
fi

source /opt/ros/humble/setup.bash
source "${ROVER_WS}/install/local_setup.bash"

export ROS_DOMAIN_ID=77
export ROS_LOCALHOST_ONLY=0

echo "ROS environment ready"
echo "  ROS_DISTRO=${ROS_DISTRO}"
echo "  ROS_DOMAIN_ID=${ROS_DOMAIN_ID}"
echo "  workspace=${ROVER_WS}"
