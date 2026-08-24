#!/usr/bin/env python3

import csv
import math
import time
from datetime import datetime
from pathlib import Path

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node


FUSED_ODOMETRY_TOPIC = "/odometry/filtered"
NODE_NAME = "print_fused_node"
DECIMAL_PLACES = 3
PRINT_PERIOD_SECONDS = 1.0
ODOMETRY_TIMEOUT_SECONDS = 5.0
LOG_DIR = Path(__file__).resolve().parent / "logs"


def quaternion_to_yaw_degrees(orientation):
    siny_cosp = 2.0 * (
        orientation.w * orientation.z
        + orientation.x * orientation.y
    )
    cosy_cosp = 1.0 - 2.0 * (
        orientation.y * orientation.y
        + orientation.z * orientation.z
    )
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


def stamp_to_seconds(stamp):
    return stamp.sec + stamp.nanosec / 1_000_000_000.0


class FusedOdometryPrinter(Node):
    def __init__(self):
        super().__init__(NODE_NAME)

        self.declare_parameter("odometry_topic", FUSED_ODOMETRY_TOPIC)
        odometry_topic = (
            self.get_parameter("odometry_topic")
            .get_parameter_value()
            .string_value
        )

        self.start_time = time.monotonic()
        self.last_print_time = 0.0
        self.last_message_time = None
        self.waiting_message_printed = False

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_name = datetime.now().strftime("fused_log_%Y%m%d_%H%M%S.csv")
        self.log_path = LOG_DIR / log_name
        self.log_file = self.log_path.open(
            "w",
            newline="",
            encoding="utf-8",
        )
        self.csv_writer = csv.writer(self.log_file)
        self.csv_writer.writerow([
            "wall_time",
            "message_time_sec",
            "frame_id",
            "child_frame_id",
            "x",
            "y",
            "z",
            "yaw_degrees",
            "linear_x",
            "angular_z",
        ])
        self.log_file.flush()

        self.subscription = self.create_subscription(
            Odometry,
            odometry_topic,
            self.odom_callback,
            10,
        )
        self.status_timer = self.create_timer(
            1.0,
            self.status_callback,
        )

        self.get_logger().info(
            f"Listening for fused odometry on {odometry_topic}"
        )
        self.get_logger().info(
            f"Logging every fused message to {self.log_path}"
        )

    def odom_callback(self, msg):
        now = time.monotonic()
        self.last_message_time = now
        self.waiting_message_printed = False

        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        twist = msg.twist.twist
        yaw_degrees = quaternion_to_yaw_degrees(orientation)
        wall_time = datetime.now().isoformat(timespec="microseconds")
        message_time = stamp_to_seconds(msg.header.stamp)

        # Log every EKF message. Do not put this after the print throttle.
        self.csv_writer.writerow([
            wall_time,
            f"{message_time:.9f}",
            msg.header.frame_id,
            msg.child_frame_id,
            f"{position.x:.9f}",
            f"{position.y:.9f}",
            f"{position.z:.9f}",
            f"{yaw_degrees:.9f}",
            f"{twist.linear.x:.9f}",
            f"{twist.angular.z:.9f}",
        ])

        # Keep terminal output readable by printing only once per second.
        if now - self.last_print_time < PRINT_PERIOD_SECONDS:
            return

        print(
            "Fused odometry | "
            f"x={position.x:.{DECIMAL_PLACES}f} m, "
            f"y={position.y:.{DECIMAL_PLACES}f} m, "
            f"z={position.z:.{DECIMAL_PLACES}f} m, "
            f"yaw={yaw_degrees:.{DECIMAL_PLACES}f} deg, "
            f"vx={twist.linear.x:.{DECIMAL_PLACES}f} m/s, "
            f"wz={twist.angular.z:.{DECIMAL_PLACES}f} rad/s"
        )

        self.log_file.flush()
        self.last_print_time = now

    def status_callback(self):
        now = time.monotonic()

        if self.last_message_time is None:
            elapsed = now - self.start_time
            if (
                elapsed >= ODOMETRY_TIMEOUT_SECONDS
                and not self.waiting_message_printed
            ):
                self.get_logger().warning(
                    "No fused odometry received yet. "
                    "Check the EKF node, topic names, and simulation clock."
                )
                self.waiting_message_printed = True
            return

        if now - self.last_message_time > ODOMETRY_TIMEOUT_SECONDS:
            self.get_logger().warning(
                "No fused odometry received for "
                f"{ODOMETRY_TIMEOUT_SECONDS:.0f} seconds."
            )
            self.last_message_time = now

    def destroy_node(self):
        if not self.log_file.closed:
            self.log_file.flush()
            self.log_file.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = FusedOdometryPrinter()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Stopping fused odometry logger.")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
