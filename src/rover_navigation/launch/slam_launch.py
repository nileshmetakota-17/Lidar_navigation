#!/usr/bin/env python3
"""SLAM Toolbox mapping from a raw Livox cloud converted to LaserScan."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

NAV_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = NAV_DIR / "config"
DEFAULT_SLAM_PARAMS = CONFIG_DIR / "slam_toolbox_params.yaml"
DEFAULT_PCL2SCAN_PARAMS = CONFIG_DIR / "pointcloud_to_laserscan_params.yaml"
DEFAULT_RVIZ_CONFIG = NAV_DIR / "rviz" / "slam.rviz"


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time")
    use_pcl2scan = LaunchConfiguration("pointcloud_to_laserscan")

    pcl2scan_node = Node(
        package="pointcloud_to_laserscan",
        executable="pointcloud_to_laserscan_node",
        name="pointcloud_to_laserscan",
        output="screen",
        remappings=[
            ("cloud_in", LaunchConfiguration("cloud_in")),
            ("scan", LaunchConfiguration("scan_topic")),
        ],
        parameters=[
            LaunchConfiguration("pcl2scan_params_file"),
            {
                "use_sim_time": use_sim_time,
                "qos_overrides./scan.publisher.reliability": "reliable",
            },
        ],
        condition=IfCondition(use_pcl2scan),
    )

    slam_toolbox = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("slam_toolbox"),
                "launch",
                "online_sync_launch.py",
            )
        ),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "slam_params_file": LaunchConfiguration("slam_params_file"),
        }.items(),
    )

    rviz_node = Node(
        package="rviz2",
        executable="rviz2",
        name="slam_rviz2",
        output="screen",
        arguments=["-d", LaunchConfiguration("rviz_config")],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(LaunchConfiguration("rviz")),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="Use simulation clock",
        ),
        DeclareLaunchArgument(
            "slam_params_file",
            default_value=str(DEFAULT_SLAM_PARAMS),
            description="slam_toolbox parameter file",
        ),
        DeclareLaunchArgument(
            "pcl2scan_params_file",
            default_value=str(DEFAULT_PCL2SCAN_PARAMS),
            description="pointcloud_to_laserscan parameter file",
        ),
        DeclareLaunchArgument(
            "pointcloud_to_laserscan",
            default_value="true",
            description="Launch pointcloud_to_laserscan (raw Livox cloud -> /scan)",
        ),
        DeclareLaunchArgument(
            "cloud_in",
            default_value="/livox/lidar",
            description="Input raw PointCloud2 topic from the Livox driver",
        ),
        DeclareLaunchArgument(
            "scan_topic",
            default_value="/scan",
            description="Output LaserScan topic for slam_toolbox",
        ),
        DeclareLaunchArgument(
            "rviz",
            default_value="true",
            description="Launch RViz with the rover SLAM configuration",
        ),
        DeclareLaunchArgument(
            "rviz_config",
            default_value=str(DEFAULT_RVIZ_CONFIG),
            description="RViz configuration file",
        ),
        LogInfo(
            msg=[
                "slam: slam_toolbox mapping, pcl2scan=",
                use_pcl2scan,
                ", cloud_in=",
                LaunchConfiguration("cloud_in"),
                ", scan=",
                LaunchConfiguration("scan_topic"),
            ]
        ),
        pcl2scan_node,
        slam_toolbox,
        rviz_node,
    ])
