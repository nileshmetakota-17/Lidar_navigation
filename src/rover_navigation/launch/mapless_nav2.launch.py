#!/usr/bin/env python3

"""Mapless Nav2 launch for ROS 2 Humble.

Starts:
  - pointcloud_to_laserscan
  - Nav2 planner/controller/BT/behavior/waypoint/smoother servers
  - Nav2 lifecycle manager
  - rover control command multiplexer (optional, enabled by default)
  - RViz (optional)

Velocity chain:
  controller_server / behavior_server -> /cmd_vel_nav
  velocity_smoother                  -> /cmd_vel_nav_smoothed

Control chain:
  /cmd_vel_nav_smoothed -> twist_mux -> /cmd_vel -> rover base driver
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    SetEnvironmentVariable,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterFile
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    package_name = "rover_navigation"

    use_sim_time = LaunchConfiguration("use_sim_time")
    autostart = LaunchConfiguration("autostart")
    use_respawn = LaunchConfiguration("use_respawn")
    log_level = LaunchConfiguration("log_level")

    params_file = LaunchConfiguration("params_file")
    pointcloud_params_file = LaunchConfiguration("pointcloud_params_file")
    rviz_config = LaunchConfiguration("rviz_config")
    start_rviz = LaunchConfiguration("rviz")
    start_control = LaunchConfiguration("start_control")
    ekf_launch = LaunchConfiguration("ekf_launch")

    cloud_topic = LaunchConfiguration("cloud_topic")
    scan_topic = LaunchConfiguration("scan_topic")

    lifecycle_nodes = [
        "controller_server",
        "smoother_server",
        "planner_server",
        "behavior_server",
        "bt_navigator",
        "waypoint_follower",
        "velocity_smoother",
    ]

    # Apply launch-time values to every node in the Nav2 parameter file.
    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            param_rewrites={
                "use_sim_time": use_sim_time,
                "autostart": autostart,
            },
            convert_types=True,
        ),
        allow_substs=True,
    )

    tf_remappings = [
        ("/tf", "tf"),
        ("/tf_static", "tf_static"),
    ]

    return LaunchDescription(
        [
            SetEnvironmentVariable("RCUTILS_LOGGING_BUFFERED_STREAM", "1"),

            DeclareLaunchArgument(
                "use_sim_time",
                default_value="False",
                description="Use simulation clock",
            ),
            DeclareLaunchArgument(
                "autostart",
                default_value="True",
                description="Automatically activate Nav2 lifecycle nodes",
            ),
            DeclareLaunchArgument(
                "use_respawn",
                default_value="False",
                description="Respawn Nav2 servers if they exit",
            ),
            DeclareLaunchArgument(
                "log_level",
                default_value="info",
                description="ROS log level",
            ),
            DeclareLaunchArgument(
                "rviz",
                default_value="False",
                description="Start RViz",
            ),
            DeclareLaunchArgument(
                "start_control",
                default_value="True",
                description="Start twist_mux and forward Nav2 commands to /cmd_vel",
            ),
            DeclareLaunchArgument(
                "ekf_launch",
                default_value="True",
                description="Start ekf_launch and fuse the odom and imu to /odometry/filtered",
            ),
            DeclareLaunchArgument(
                "params_file",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare(package_name),
                        "config",
                        "nav2_mapless_params.yaml",
                    ]
                ),
                description="Full path to the mapless Nav2 YAML file",
            ),
            DeclareLaunchArgument(
                "pointcloud_params_file",
                default_value=PathJoinSubstitution(
                    [
                        FindPackageShare(package_name),
                        "config",
                        "pointcloud_to_laserscan_params.yaml",
                    ]
                ),
                description="Full path to pointcloud_to_laserscan parameters",
            ),
            DeclareLaunchArgument(
                "rviz_config",
                default_value=PathJoinSubstitution(
                    [FindPackageShare(package_name), "config", "nav2_mapless.rviz"]
                ),
                description="Full path to the RViz configuration",
            ),
            DeclareLaunchArgument(
                "cloud_topic",
                default_value="/livox/lidar",
                description="Input PointCloud2 topic",
            ),
            DeclareLaunchArgument(
                "scan_topic",
                default_value="/scan",
                description="Output LaserScan topic",
            ),

            # Make this launch self-contained, matching nav2_launch.py: forward
            # /cmd_vel_nav_smoothed to the rover's /cmd_vel command topic.
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [
                            FindPackageShare("rover_control"),
                            "launch",
                            "control.launch.py",
                        ]
                    )
                ),
                condition=IfCondition(start_control),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    PathJoinSubstitution(
                        [
                            FindPackageShare("rover_localization"),
                            "launch",
                            "ekf.launch.py",
                        ]
                    )
                ),
                condition=IfCondition(ekf_launch),
            ),

            # Convert the Livox PointCloud2 stream to the LaserScan consumed by Nav2.
            Node(
                package="pointcloud_to_laserscan",
                executable="pointcloud_to_laserscan_node",
                name="pointcloud_to_laserscan",
                output="screen",
                parameters=[pointcloud_params_file, {"use_sim_time": use_sim_time}],
                remappings=[
                    ("cloud_in", cloud_topic),
                    ("scan", scan_topic),
                ],
                arguments=["--ros-args", "--log-level", log_level],
            ),

            Node(
                package="nav2_controller",
                executable="controller_server",
                name="controller_server",
                output="screen",
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
                remappings=tf_remappings + [("cmd_vel", "cmd_vel_nav")],
            ),

            Node(
                package="nav2_smoother",
                executable="smoother_server",
                name="smoother_server",
                output="screen",
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
                remappings=tf_remappings,
            ),

            Node(
                package="nav2_planner",
                executable="planner_server",
                name="planner_server",
                output="screen",
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
                remappings=tf_remappings,
            ),

            Node(
                package="nav2_behaviors",
                executable="behavior_server",
                name="behavior_server",
                output="screen",
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
                remappings=tf_remappings + [("cmd_vel", "cmd_vel_nav")],
            ),

            Node(
                package="nav2_bt_navigator",
                executable="bt_navigator",
                name="bt_navigator",
                output="screen",
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
                remappings=tf_remappings,
            ),

            Node(
                package="nav2_waypoint_follower",
                executable="waypoint_follower",
                name="waypoint_follower",
                output="screen",
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
                remappings=tf_remappings,
            ),

            # Input: /cmd_vel_nav. Output: /cmd_vel_nav_smoothed.
            Node(
                package="nav2_velocity_smoother",
                executable="velocity_smoother",
                name="velocity_smoother",
                output="screen",
                respawn=use_respawn,
                respawn_delay=2.0,
                parameters=[configured_params],
                arguments=["--ros-args", "--log-level", log_level],
                remappings=tf_remappings
                + [
                    ("cmd_vel", "cmd_vel_nav"),
                    ("cmd_vel_smoothed", "cmd_vel_nav_smoothed"),
                ],
            ),

            Node(
                package="nav2_lifecycle_manager",
                executable="lifecycle_manager",
                name="lifecycle_manager_navigation",
                output="screen",
                parameters=[
                    {"use_sim_time": use_sim_time},
                    {"autostart": autostart},
                    {"node_names": lifecycle_nodes},
                ],
            ),

            Node(
                condition=IfCondition(start_rviz),
                package="rviz2",
                executable="rviz2",
                name="rviz",
                output="screen",
                arguments=["-d", rviz_config],
                parameters=[{"use_sim_time": use_sim_time}],
                remappings=tf_remappings,
            ),
        ]
    )
