"""Base rover control: command arbitration and hardware UDP bridge."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    control_dir = get_package_share_directory("rover_control")
    navigation_topic = LaunchConfiguration("navigation_topic")

    return LaunchDescription([
        DeclareLaunchArgument(
            "navigation_topic",
            default_value="/cmd_vel_nav_smoothed",
            description="Navigation velocity topic consumed by twist_mux",
        ),
        Node(
            package="twist_mux",
            executable="twist_mux",
            name="twist_mux",
            output="screen",
            parameters=[
                os.path.join(control_dir, "config", "twist_mux.yaml"),
                {"topics.navigation.topic": navigation_topic},
            ],
            remappings=[
                ("/cmd_vel_out", "/cmd_vel"),
            ],
        ),
        
    ])
