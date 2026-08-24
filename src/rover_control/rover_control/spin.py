
#!/usr/bin/env python3

import argparse
import select
import sys
import termios
import time
import tty

import rclpy
from geometry_msgs.msg import Twist
from rclpy.utilities import remove_ros_args


NODE_NAME = "keyboard_spin_node"
CMD_VEL_TOPIC = "/cmd_vel_keyboard"
QUEUE_SIZE = 10

DEFAULT_ANGULAR_SPEED = 0.3

# Speed changes by this amount for each key press.
SPEED_STEP = 0.1

# Maximum allowed angular speed.
MAX_ANGULAR_SPEED = 3.0

# Publish commands at approximately 50 Hz.
CONTROL_PERIOD = 0.02


def clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def make_twist(angular_z=0.0):
    command = Twist()
    command.linear.x = 0.0
    command.angular.z = float(angular_z)
    return command


def publish_stop(publisher):
    stop_command = make_twist()

    for _ in range(10):
        publisher.publish(stop_command)
        time.sleep(0.02)


def get_initial_speed():
    application_args = remove_ros_args(args=sys.argv)

    parser = argparse.ArgumentParser(
        description=(
            "Continuously spin the robot and change speed "
            "using keyboard commands."
        )
    )

    parser.add_argument(
        "speed",
        nargs="?",
        type=float,
        default=DEFAULT_ANGULAR_SPEED,
        help=(
            "Initial angular speed in rad/s. "
            "Positive is counterclockwise and "
            "negative is clockwise."
        ),
    )

    arguments = parser.parse_args(application_args[1:])

    return clamp(
        arguments.speed,
        -MAX_ANGULAR_SPEED,
        MAX_ANGULAR_SPEED,
    )


def read_key():
    """
    Read one keyboard key without blocking the control loop.
    """
    readable, _, _ = select.select(
        [sys.stdin],
        [],
        [],
        0.0,
    )

    if readable:
        return sys.stdin.read(1)

    return None


def print_controls():
    print()
    print("Keyboard controls")
    print("-----------------")
    print("+ or w : increase speed")
    print("- or s : decrease speed")
    print("r      : reverse direction")
    print("0      : stop rotation")
    print("q      : quit")
    print()


def main():
    angular_speed = get_initial_speed()

    rclpy.init(args=sys.argv)
    node = rclpy.create_node(NODE_NAME)

    publisher = node.create_publisher(
        Twist,
        CMD_VEL_TOPIC,
        QUEUE_SIZE,
    )

    # Save the current terminal settings so they can be restored.
    old_terminal_settings = termios.tcgetattr(sys.stdin)

    print_controls()

    node.get_logger().info(
        f"Initial angular speed: {angular_speed:.2f} rad/s"
    )

    try:
        # Allow keys to be read immediately without pressing Enter.
        tty.setcbreak(sys.stdin.fileno())

        running = True

        while rclpy.ok() and running:
            key = read_key()

            if key is not None:
                key = key.lower()

                if key in ("+", "=", "w"):
                    # Preserve the current direction.
                    if angular_speed < 0.0:
                        angular_speed -= SPEED_STEP
                    else:
                        angular_speed += SPEED_STEP

                    angular_speed = clamp(
                        angular_speed,
                        -MAX_ANGULAR_SPEED,
                        MAX_ANGULAR_SPEED,
                    )

                    node.get_logger().info(
                        f"Speed increased: "
                        f"{angular_speed:.2f} rad/s"
                    )

                elif key in ("-", "_", "s"):
                    # Reduce the speed magnitude.
                    if angular_speed > 0.0:
                        angular_speed -= SPEED_STEP
                        angular_speed = max(
                            0.0,
                            angular_speed,
                        )

                    elif angular_speed < 0.0:
                        angular_speed += SPEED_STEP
                        angular_speed = min(
                            0.0,
                            angular_speed,
                        )

                    node.get_logger().info(
                        f"Speed decreased: "
                        f"{angular_speed:.2f} rad/s"
                    )

                elif key == "r":
                    angular_speed = -angular_speed

                    # If currently stopped, start slowly clockwise.
                    if angular_speed == 0.0:
                        angular_speed = -SPEED_STEP

                    node.get_logger().info(
                        f"Direction reversed: "
                        f"{angular_speed:.2f} rad/s"
                    )

                elif key == "0":
                    angular_speed = 0.0

                    node.get_logger().info(
                        "Rotation stopped. "
                        "Press + or w to start again."
                    )

                elif key == "q":
                    node.get_logger().info(
                        "Quit command received."
                    )
                    running = False
                    continue

                elif key == "\x03":
                    # Ctrl+C
                    running = False
                    continue

            publisher.publish(
                make_twist(
                    angular_z=angular_speed,
                )
            )

            rclpy.spin_once(
                node,
                timeout_sec=CONTROL_PERIOD,
            )

    except KeyboardInterrupt:
        node.get_logger().info(
            "Keyboard interrupt received."
        )

    finally:
        # Restore normal terminal behavior.
        termios.tcsetattr(
            sys.stdin,
            termios.TCSADRAIN,
            old_terminal_settings,
        )

        publish_stop(publisher)

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()

'''
+ or w  → increase speed
- or s  → decrease speed
r       → reverse direction
0       → stop rotation
q       → quit
'''
