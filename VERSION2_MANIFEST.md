# Version 2 Portable Archive

Archive: `rover_ros_ws_version2.zip`

Included:

- `src/rover_control`
- `src/rover_localization` (runtime logs excluded)
- `src/rover_navigation` (deployable map images/YAML included)
- `src/livox_ros_driver2`
- root helper scripts, documentation, and magnetometer Python utilities

Excluded because they are generated, machine-specific, or unnecessary for a
clean deployment:

- all `build/`, `install/`, and `log/` output
- nested Git metadata and Python caches
- the Python virtual environment under `mag/imu_vis_env`
- FAST-LIO (`src/FAST_LIO_ROS2`) and its launch helpers
- the 22 GB Isaac ROS development workspace under `src/workspaces`
- recorded performance/localization logs
- SLAM Toolbox `.data` and `.posegraph` editing state (deployable `.pgm` and
  `.yaml` maps remain included)

See `SETUP_VERSION2.md` after extracting.

Recreate the archive at any time with:

```bash
./scripts/create_portable_zip.sh
```

The generated file is written to `dist/rover_ros_ws_version2.zip`.
