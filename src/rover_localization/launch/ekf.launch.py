from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    package_share = Path(
        get_package_share_directory("rover_localization")
    )

    ekf_config = package_share / "config" / "ekf.yaml"
    rviz_config = package_share / "config" / "odometry.rviz"
    robot_model = package_share / "urdf" / "rover.urdf"

    robot_description = ParameterValue(
        Command([
            "xacro ",
            str(robot_model),
        ]),
        value_type=str,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "start_rviz",
            default_value="false",
            description="Start RViz with the rover odometry configuration",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="Use the simulation clock",
        ),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            parameters=[{
                "robot_description": robot_description,
                "use_sim_time": LaunchConfiguration("use_sim_time"),
            }],
            output="screen",
        ),

        Node(
            package="robot_localization",
            executable="ekf_node",
            name="ekf_filter_node",
            parameters=[str(ekf_config)],
            output="screen",
        ),

        Node(
            package="rover_localization",
            executable="odom_to_path",
            name="fused_odom_to_path",
            parameters=[{
                "odometry_topic": "/odometry/filtered",
                "path_topic": "/model/rover/path_fused",
                "minimum_point_distance": 0.005,
                "publish_period": 0.05,
            }],
            output="screen",
        ),
        #  Node(
        #     package="joint_state_publisher",
        #     executable="joint_state_publisher",
        #     name="joint_state_publisher",
        #     parameters=[{
        #         "robot_description": robot_description,
        #         "use_sim_time": LaunchConfiguration("use_sim_time"),
        #     }],
        #     output="screen",
        # ),
        Node(
            package="rover_localization",
            executable="odom_to_path",
            name="raw_odom_to_path",
            parameters=[{
                "odometry_topic": "/odom",
                "path_topic": "/model/rover/path_raw",
                "minimum_point_distance": 0.005,
                "publish_period": 0.05,
            }],
            output="screen",
        ),
        Node(
            package="rviz2",
            executable="rviz2",
            name="rover_odometry_rviz",
            arguments=["-d", str(rviz_config)],
            condition=IfCondition(LaunchConfiguration("start_rviz")),
            output="screen",
        ),
    ])
