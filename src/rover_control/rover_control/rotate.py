
#!/usr/bin/env python3

import argparse
import math
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.utilities import remove_ros_args


NODE_NAME = "rotate_by_angle_node"
CMD_VEL_TOPIC = "/cmd_vel_keyboard"

# Change this to "/odometry/filtered" when using EKF fusion.
ODOMETRY_TOPIC = "/odometry/filtered"

QUEUE_SIZE = 10

# Used when no angle is provided.
DEFAULT_ROTATION_DEGREES = 90.0

# Rotation controller settings.
ANGULAR_KP = 1.2
MAX_ANGULAR_SPEED = 0.5
MIN_ANGULAR_SPEED = 0.08

# Stop when the remaining error is within 1 degree.
ANGLE_TOLERANCE = math.radians(1.0)

# Approximately 50 Hz.
CONTROL_PERIOD = 0.02

current_yaw = None


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def normalize_angle(angle):
    """
    Normalize an angle to the range -pi to +pi.
    """
    return math.atan2(math.sin(angle), math.cos(angle))


def quaternion_to_yaw(orientation):
    """
    Convert a ROS quaternion into yaw in radians.
    """
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
    global current_yaw

    current_yaw = quaternion_to_yaw(
        msg.pose.pose.orientation
    )


def make_twist(linear_x=0.0, angular_z=0.0):
    command = Twist()
    command.linear.x = float(linear_x)
    command.angular.z = float(angular_z)
    return command


def publish_stop(publisher):
    """
    Publish several zero-velocity commands to make sure the robot stops.
    """
    stop_command = make_twist()

    for _ in range(5):
        publisher.publish(stop_command)
        time.sleep(0.02)


def get_requested_rotation():
    """
    Read the requested relative rotation from the command line.
    """
    application_args = remove_ros_args(args=sys.argv)

    parser = argparse.ArgumentParser(
        description=(
            "Rotate the robot by a relative angle using odometry."
        )
    )

    parser.add_argument(
        "degrees",
        nargs="?",
        type=float,
        default=DEFAULT_ROTATION_DEGREES,
        help=(
            "Relative rotation in degrees. "
            "Positive is counterclockwise; "
            "negative is clockwise."
        ),
    )

    arguments = parser.parse_args(application_args[1:])
    return arguments.degrees


def main():
    global current_yaw

    requested_degrees = get_requested_rotation()
    requested_radians = math.radians(requested_degrees)

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

        while rclpy.ok() and current_yaw is None:
            rclpy.spin_once(
                node,
                timeout_sec=CONTROL_PERIOD,
            )

        if not rclpy.ok():
            return

        if abs(requested_radians) <= ANGLE_TOLERANCE:
            node.get_logger().info(
                "Requested rotation is already within tolerance."
            )
            return

        start_yaw = current_yaw

        # Track accumulated rotation instead of only comparing the
        # normalized start and target yaw. This allows rotations such
        # as 180, 270, or 360 degrees.
        accumulated_rotation = 0.0
        previous_yaw = current_yaw

        rotation_direction = (
            1.0 if requested_radians > 0.0 else -1.0
        )

        direction_name = (
            "counterclockwise"
            if rotation_direction > 0.0
            else "clockwise"
        )

        node.get_logger().info(
            f"Start yaw={math.degrees(start_yaw):.2f} deg, "
            f"requested rotation={requested_degrees:.2f} deg, "
            f"direction={direction_name}"
        )

        while rclpy.ok():
            rclpy.spin_once(
                node,
                timeout_sec=CONTROL_PERIOD,
            )

            if current_yaw is None:
                continue

            # Calculate the yaw change since the previous odometry
            # message and handle the -pi/+pi wraparound.
            yaw_change = normalize_angle(
                current_yaw - previous_yaw
            )

            accumulated_rotation += yaw_change
            previous_yaw = current_yaw

            remaining_angle = (
                requested_radians - accumulated_rotation
            )

            # Stop when close enough to the requested angle.
            if abs(remaining_angle) <= ANGLE_TOLERANCE:
                publish_stop(publisher)

                node.get_logger().info(
                    f"Rotation complete. "
                    f"requested={requested_degrees:.2f} deg, "
                    f"rotated={math.degrees(accumulated_rotation):.2f} deg, "
                    f"final_yaw={math.degrees(current_yaw):.2f} deg"
                )
                break

            # Stop if the robot crosses the requested angle.
            crossed_target = (
                rotation_direction > 0.0
                and accumulated_rotation >= requested_radians
            ) or (
                rotation_direction < 0.0
                and accumulated_rotation <= requested_radians
            )

            if crossed_target:
                publish_stop(publisher)

                node.get_logger().warning(
                    f"Rotation target crossed. "
                    f"requested={requested_degrees:.2f} deg, "
                    f"rotated={math.degrees(accumulated_rotation):.2f} deg"
                )
                break

            # Proportional angular-speed controller.
            angular_z = ANGULAR_KP * remaining_angle

            angular_z = clamp(
                angular_z,
                -MAX_ANGULAR_SPEED,
                MAX_ANGULAR_SPEED,
            )

            # Maintain enough angular velocity to overcome motor
            # deadband near the target.
            if (
                0.0 < abs(angular_z) < MIN_ANGULAR_SPEED
            ):
                angular_z = math.copysign(
                    MIN_ANGULAR_SPEED,
                    angular_z,
                )

            publisher.publish(
                make_twist(
                    linear_x=0.0,
                    angular_z=angular_z,
                )
            )

    except KeyboardInterrupt:
        node.get_logger().info(
            "Rotation interrupted by the user."
        )

    finally:
        publish_stop(publisher)
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
