import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

def generate_launch_description():
    control_dir = get_package_share_directory("rover_control")

    return LaunchDescription([
        DeclareLaunchArgument(
            "start_control",
            default_value="true",
            description="Start twist_mux",
        ),
        DeclareLaunchArgument("device_id", default_value="0"),
        DeclareLaunchArgument("axis_linear", default_value="1"),
        DeclareLaunchArgument("axis_angular", default_value="3"),
        DeclareLaunchArgument("linear_kp", default_value="4.0"),
        DeclareLaunchArgument("angular_kp", default_value="5.0"),
        DeclareLaunchArgument("enable_button", default_value="5"),
        DeclareLaunchArgument("stop_button", default_value="1"),
        DeclareLaunchArgument("solo_button", default_value="0"),
        DeclareLaunchArgument("temporary_button", default_value="2"),
        DeclareLaunchArgument("debug_joy", default_value="false"),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(control_dir, "launch", "control.launch.py"),
            ),
            condition=IfCondition(LaunchConfiguration("start_control")),
        ),
        Node(
            package="joy",
            executable="joy_node",
            name="joy_node",
            parameters=[{
                "device_id": ParameterValue(
                    LaunchConfiguration("device_id"),
                    value_type=int,
                ),
                "deadzone": 0.05,
                "autorepeat_rate": 50.0,
            }],
            output="screen",
        ),
        Node(
            package="rover_control",
            executable="joy_control",
            name="sony_joy_rover_teleop",
            parameters=[{
                "cmd_vel_topic": "/cmd_vel_joy",
                "axis_linear": ParameterValue(
                    LaunchConfiguration("axis_linear"),
                    value_type=int,
                ),
                "axis_angular": ParameterValue(
                    LaunchConfiguration("axis_angular"),
                    value_type=int,
                ),
                "linear_kp": ParameterValue(
                    LaunchConfiguration("linear_kp"),
                    value_type=float,
                ),
                "angular_kp": ParameterValue(
                    LaunchConfiguration("angular_kp"),
                    value_type=float,
                ),
                "require_enable": True,
                "enable_button": ParameterValue(
                    LaunchConfiguration("enable_button"),
                    value_type=int,
                ),
                "stop_button": ParameterValue(
                    LaunchConfiguration("stop_button"),
                    value_type=int,
                ),
                "solo_button": ParameterValue(
                    LaunchConfiguration("solo_button"),
                    value_type=int,
                ),
                "temporary_button": ParameterValue(
                    LaunchConfiguration("temporary_button"),
                    value_type=int,
                ),
                "debug_joy": ParameterValue(
                    LaunchConfiguration("debug_joy"),
                    value_type=bool,
                ),
            }],
            output="screen",
        ),
    ])
