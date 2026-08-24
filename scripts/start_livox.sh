#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/rover_env.sh"

HOST_IP="192.168.10.1"
LIDAR_IP="192.168.10.147"
SOURCE_CONFIG="${ROVER_WS}/src/livox_ros_driver2/config/MID360s_config.json"
INSTALLED_CONFIG="${ROVER_WS}/install/livox_ros_driver2/share/livox_ros_driver2/config/MID360s_config.json"

if ! ip -brief address | grep -Fq "${HOST_IP}/"; then
  echo "ERROR: host IP ${HOST_IP} is not assigned to an active interface." >&2
  ip -brief address >&2
  exit 1
fi

if [[ ! -f "${SOURCE_CONFIG}" || ! -f "${INSTALLED_CONFIG}" ]]; then
  echo "ERROR: MID360S configuration file is missing." >&2
  echo "  source:    ${SOURCE_CONFIG}" >&2
  echo "  installed: ${INSTALLED_CONFIG}" >&2
  exit 1
fi

if ! grep -Fq "\"host_ip\"        : \"${HOST_IP}\"" "${SOURCE_CONFIG}"; then
  echo "ERROR: source MID360S config does not use host IP ${HOST_IP}." >&2
  exit 1
fi

if ! grep -Fq "\"ip\" : \"${LIDAR_IP}\"" "${SOURCE_CONFIG}"; then
  echo "ERROR: source MID360S config does not use lidar IP ${LIDAR_IP}." >&2
  exit 1
fi

# Keep the generated install copy synchronized even after an incomplete build.
if ! cmp -s "${SOURCE_CONFIG}" "${INSTALLED_CONFIG}"; then
  cp "${SOURCE_CONFIG}" "${INSTALLED_CONFIG}"
  echo "Updated installed MID360S network configuration."
fi

LIVOX_HOST_PORTS=':(56101|56201|56301|56401|56501) '
if ss -lunp | grep -Eq "${LIVOX_HOST_PORTS}"; then
  echo "ERROR: a Livox host UDP port is already in use; another driver may be running." >&2
  ss -lunp | grep -E "${LIVOX_HOST_PORTS}" >&2 || true
  exit 1
fi

echo "Starting MID360S driver: host=${HOST_IP}, lidar=${LIDAR_IP}"
exec ros2 launch livox_ros_driver2 msg_MID360s_launch.py "$@"
