#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE_NAME="$(basename -- "${WORKSPACE_DIR}")"
OUTPUT_DIR="${WORKSPACE_DIR}/dist"
OUTPUT_FILE="${OUTPUT_DIR}/rover_ros_ws_version2.zip"

command -v zip >/dev/null 2>&1 || {
  echo "Error: zip is not installed. Run: sudo apt install zip" >&2
  exit 1
}

mkdir -p -- "${OUTPUT_DIR}"

# Run from the parent so the archive has one top-level workspace directory.
# -FS also removes entries from an older archive when they are now excluded.
cd -- "$(dirname -- "${WORKSPACE_DIR}")"
zip -r -FS "${OUTPUT_FILE}" "${WORKSPACE_NAME}" \
  -x "${WORKSPACE_NAME}/build/*" \
     "${WORKSPACE_NAME}/install/*" \
     "${WORKSPACE_NAME}/log/*" \
     "${WORKSPACE_NAME}/dist/*" \
     "${WORKSPACE_NAME}/.git/*" \
     "${WORKSPACE_NAME}/.agents/*" \
     "${WORKSPACE_NAME}/.codex/*" \
     "${WORKSPACE_NAME}/src/FAST_LIO_ROS2/*" \
     "${WORKSPACE_NAME}/src/workspaces/*" \
     "${WORKSPACE_NAME}/mag/imu_vis_env/*" \
     "*/__pycache__/*" "*.pyc" "*.pyo" \
     "*.data" "*.posegraph" "*.log"

echo
echo "Portable archive created: ${OUTPUT_FILE}"
du -h -- "${OUTPUT_FILE}"
sha256sum -- "${OUTPUT_FILE}"
