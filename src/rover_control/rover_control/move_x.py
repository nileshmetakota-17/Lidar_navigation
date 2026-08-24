#!/usr/bin/env python3

import argparse
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.utilities import remove_ros_args


NODE_NAME = "move_to_x_node"
CMD_VEL_TOPIC = "/cmd_vel_keyboard"
ODOMETRY_TOPIC = "/odom"
QUEUE_SIZE = 10

# Used when no distance is supplied on the command line.
DEFAULT_DISTANCE_X = 3.0

# Linear movement controller.
LINEAR_KP = 0.4
MAX_LINEAR_SPEED = 0.6
MIN_LINEAR_SPEED = 0.06
POSITION_TOLERANCE = 0.03

# Robot should face the positive odometry X direction.
TARGET_YAW = 0.0
YAW_KP = 2.0
MAX_ANGULAR_SPEED = 0.5
YAW_TOLERANCE = math.radians(3.0)

# Stop translation and correct orientation when yaw error is large.
MAX_MOVING_YAW_ERROR = math.radians(15.0)

# Approximately 50 Hz.
CONTROL_PERIOD = 0.02

current_x = None
current_yaw = None


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def normalize_angle(angle):
    return math.atan2(math.sin(angle), math.cos(angle))


def quaternion_to_yaw(orientation):
    siny_cosp = 2.0 * (
        orientation.w * orientation.z
        + orientation.x * orientation.y
    )

    cosy_cosp = 1.0 - 2.0 * (
        orientation.y * orientation.y
        + orientation.z * orientation.z
    )

    return math.atan2(siny_cosp, cosy_cosp)


def odom_callback(msg):
    global current_x, current_yaw

    current_x = msg.pose.pose.position.x
    current_yaw = quaternion_to_yaw(
        msg.pose.pose.orientation
    )


def make_twist(linear_x=0.0, angular_z=0.0):
    command = Twist()
    command.linear.x = float(linear_x)
    command.angular.z = float(angular_z)
    return command


def publish_stop(publisher):
    """Publish several stop commands for reliability."""
    stop_command = make_twist()

    for _ in range(5):
        publisher.publish(stop_command)
        time.sleep(0.02)


def get_requested_distance():
    # Remove ROS-specific arguments before parsing our distance.
    application_args = remove_ros_args(args=sys.argv)

    parser = argparse.ArgumentParser(
        description="Move the robot along odometry X by a relative distance."
    )

    parser.add_argument(
        "distance",
        nargs="?",
        type=float,
        default=DEFAULT_DISTANCE_X,
        help=(
            "Relative X distance in metres. "
            "Positive moves forward; negative moves backward."
        ),
    )

    arguments = parser.parse_args(application_args[1:])
    return arguments.distance


def main():
    global current_x, current_yaw

    requested_distance = get_requested_distance()

    rclpy.init(args=sys.argv)
    node = rclpy.create_node(NODE_NAME)

    publisher = node.create_publisher(
        Twist,
        CMD_VEL_TOPIC,
        QUEUE_SIZE,
    )

    subscription = node.create_subscription(
        Odometry,
        ODOMETRY_TOPIC,
        odom_callback,
        QUEUE_SIZE,
    )

    # Keep the subscription alive.
    _ = subscription

    try:
        node.get_logger().info("Waiting for odometry...")

        while rclpy.ok() and (
            current_x is None or current_yaw is None
        ):
            rclpy.spin_once(
                node,
                timeout_sec=CONTROL_PERIOD,
            )

        if not rclpy.ok():
            return

        start_x = current_x

        # Relative target:
        # starting position + requested movement distance.
        target_x = start_x + requested_distance

        node.get_logger().info(
            f"Start x={start_x:.3f} m, "
            f"requested distance={requested_distance:.3f} m, "
            f"target x={target_x:.3f} m"
        )

        if abs(requested_distance) <= POSITION_TOLERANCE:
            node.get_logger().info(
                "Requested distance is already within tolerance."
            )
            return

        movement_direction = (
            1.0 if requested_distance > 0.0 else -1.0
        )

        direction_name = (
            "forward"
            if movement_direction > 0.0
            else "backward"
        )

        node.get_logger().info(
            f"Moving {direction_name}."
        )

        while rclpy.ok():
            rclpy.spin_once(
                node,
                timeout_sec=CONTROL_PERIOD,
            )

            if current_x is None or current_yaw is None:
                continue

            position_error = target_x - current_x

            # Stop when close enough.
            if abs(position_error) <= POSITION_TOLERANCE:
                publish_stop(publisher)

                travelled_distance = current_x - start_x

                node.get_logger().info(
                    f"Target reached. "
                    f"target_x={target_x:.3f}, "
                    f"current_x={current_x:.3f}, "
                    f"travelled={travelled_distance:.3f} m"
                )
                break

            # Stop if inertia caused the robot to cross the target.
            crossed_target = (
                movement_direction > 0.0
                and current_x >= target_x
            ) or (
                movement_direction < 0.0
                and current_x <= target_x
            )

            if crossed_target:
                publish_stop(publisher)

                travelled_distance = current_x - start_x

                node.get_logger().warning(
                    f"Target crossed. "
                    f"target_x={target_x:.3f}, "
                    f"current_x={current_x:.3f}, "
                    f"travelled={travelled_distance:.3f} m"
                )
                break

            # Correct the robot's heading.
            yaw_error = normalize_angle(
                TARGET_YAW - current_yaw
            )

            angular_z = clamp(
                YAW_KP * yaw_error,
                -MAX_ANGULAR_SPEED,
                MAX_ANGULAR_SPEED,
            )

            # If the robot is facing too far away from the X direction,
            # rotate in place before continuing.
            if abs(yaw_error) > MAX_MOVING_YAW_ERROR:
                linear_x = 0.0

            else:
                # Proportional linear-speed controller.
                linear_x = LINEAR_KP * position_error

                linear_x = clamp(
                    linear_x,
                    -MAX_LINEAR_SPEED,
                    MAX_LINEAR_SPEED,
                )

                # Maintain enough speed to overcome motor deadband.
                if (
                    0.0 < abs(linear_x) < MIN_LINEAR_SPEED
                ):
                    linear_x = math.copysign(
                        MIN_LINEAR_SPEED,
                        linear_x,
                    )

            publisher.publish(
                make_twist(
                    linear_x=linear_x,
                    angular_z=angular_z,
                )
            )

    except KeyboardInterrupt:
        node.get_logger().info(
            "Movement interrupted by the user."
        )

    finally:
        publish_stop(publisher)
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
