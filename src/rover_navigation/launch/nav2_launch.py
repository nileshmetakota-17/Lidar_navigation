"""Point-to-point Nav2 using raw Livox cloud and chassis/EKF odometry."""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    navigation_dir = get_package_share_directory("rover_navigation")
    control_dir = get_package_share_directory("rover_control")

    map_file = LaunchConfiguration("map")
    params_file = LaunchConfiguration("params_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_rviz = LaunchConfiguration("rviz")

    localization_dir = get_package_share_directory("rover_localization")

    ekf_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                localization_dir,
                "launch",
                "ekf.launch.py",
            )
        ),
        launch_arguments={
            "ekf_rviz": "false",
        }.items(),
    )

    control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(control_dir, "launch", "control.launch.py"),
        ),
        launch_arguments={
            # "navigation_topic": "/cmd_vel_nav_safe",
            "navigation_topic":"/cmd_vel_nav_smoothed"
        }.items(),
        condition=IfCondition(LaunchConfiguration("start_control")),
    )

    pointcloud_to_laserscan = Node(
        package="pointcloud_to_laserscan",
        executable="pointcloud_to_laserscan_node",
        name="pointcloud_to_laserscan",
        output="screen",
        parameters=[
            os.path.join(
                navigation_dir, "config", "pointcloud_to_laserscan_params.yaml"
            ),
            {"use_sim_time": use_sim_time},
        ],
        remappings=[
            ("cloud_in", "/livox/lidar"),
            ("scan", "/scan"),
        ],
    )

    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[params_file, {"yaml_filename": map_file}],
    )

    # AMCL publishes map -> odom; the EKF publishes odom -> base_link.
    amcl = Node(
        package="nav2_amcl",
        executable="amcl",
        name="amcl",
        output="screen",
        parameters=[params_file],
        remappings=[("scan", "/scan")],
    )

    planner_server = Node(
        package="nav2_planner",
        executable="planner_server",
        name="planner_server",
        output="screen",
        parameters=[params_file],
    )

    # Keep navigation commands separate until the velocity smoother validates them.
    controller_server = Node(
        package="nav2_controller",
        executable="controller_server",
        name="controller_server",
        output="screen",
        parameters=[params_file],
        remappings=[("cmd_vel", "/cmd_vel_nav")],
    )

    behavior_server = Node(
        package="nav2_behaviors",
        executable="behavior_server",
        name="behavior_server",
        output="screen",
        parameters=[params_file],
        remappings=[("cmd_vel", "/cmd_vel_nav")],
    )

    bt_navigator = Node(
        package="nav2_bt_navigator",
        executable="bt_navigator",
        name="bt_navigator",
        output="screen",
        parameters=[params_file],
    )

    waypoint_follower = Node(
        package="nav2_waypoint_follower",
        executable="waypoint_follower",
        name="waypoint_follower",
        output="screen",
        parameters=[params_file],
    )

    # Keep the smoothed Nav2 command separate for arbitration by twist_mux.
    velocity_smoother = Node(
        package="nav2_velocity_smoother",
        executable="velocity_smoother",
        name="velocity_smoother",
        output="screen",
        parameters=[params_file],
        remappings=[
            ("cmd_vel", "/cmd_vel_nav"),
            ("cmd_vel_smoothed", "/cmd_vel_nav_smoothed"),
        ],
    )

    # collision_monitor = Node(
    #     package="nav2_collision_monitor",
    #     executable="collision_monitor",
    #     name="collision_monitor",
    #     output="screen",
    #     parameters=[params_file],
    # )

    # RViz's Localization status checks this exact manager/service name.
    lifecycle_manager_localization = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_localization",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "autostart": True,
            "node_names": ["map_server", "amcl"],
        }],
    )

    lifecycle_manager_navigation = Node(
        package="nav2_lifecycle_manager",
        executable="lifecycle_manager",
        name="lifecycle_manager_navigation",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "autostart": True,
            "node_names": [
                "planner_server",
                "controller_server",
                "behavior_server",
                "bt_navigator",
                "waypoint_follower",
                "velocity_smoother",
                # "collision_monitor",
            ],
        }],
    )

    rviz = Node(
        package="rviz2",
        executable="rviz2",
        name="nav2_rviz2",
        output="screen",
        condition=IfCondition(use_rviz),
        arguments=[
            "-d",
            os.path.join(navigation_dir, "config", "nav2_.rviz"),
        ],
        parameters=[{"use_sim_time": use_sim_time}],
    )
    return LaunchDescription([
        DeclareLaunchArgument(
            "start_control",
            default_value="true",
            description="Start twist_mux and udp_bridge",
        ),
        DeclareLaunchArgument(
            "map",
            default_value="",
            description="Absolute path to the occupancy map YAML file",
        ),
        DeclareLaunchArgument(
            "params_file",
            default_value=os.path.join(
                navigation_dir, "config", "nav2_params.yaml"
            ),
            description="Absolute path to the Nav2 parameter file",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="Use simulation clock",
        ),
        DeclareLaunchArgument(
            "rviz",
            default_value="true",
            description="Start RViz",
        ),
        control_launch,
        ekf_launch,
        pointcloud_to_laserscan,
        map_server,
        amcl,
        lifecycle_manager_localization,
        planner_server,
        controller_server,
        behavior_server,
        bt_navigator,
        waypoint_follower,
        velocity_smoother,
        # collision_monitor,
        # Give map_server and AMCL time to activate before navigation servers.
        TimerAction(period=2.0, actions=[lifecycle_manager_navigation]),
        rviz,
    ])
