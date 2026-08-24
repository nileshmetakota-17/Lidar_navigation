#!/usr/bin/env python3

import csv
import math
import time
from datetime import datetime
from pathlib import Path

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node


DEFAULT_ODOMETRY_TOPIC = "/odom"
# RAW_ODOMETRY_TOPIC = "/model/rover/odometry"
NODE_NAME = "print_position_node"
DECIMAL_PLACES = 3
PRINT_PERIOD_SECONDS = 1.0
ODOMETRY_TIMEOUT_SECONDS = 5.0
LOG_DIR = Path(__file__).resolve().parent / "logs"


def quaternion_to_yaw_degrees(orientation):
    siny_cosp = 2.0 * (
        orientation.w * orientation.z +
        orientation.x * orientation.y
    )
    cosy_cosp = 1.0 - 2.0 * (
        orientation.y * orientation.y +
        orientation.z * orientation.z
    )
    return math.degrees(math.atan2(siny_cosp, cosy_cosp))


def stamp_to_seconds(stamp):
    return stamp.sec + stamp.nanosec / 1_000_000_000.0


class PositionPrinter(Node):
    def __init__(self):
        super().__init__(NODE_NAME)
        self.declare_parameter("odometry_topic", DEFAULT_ODOMETRY_TOPIC)
        odometry_topic = (
            self.get_parameter("odometry_topic").get_parameter_value().string_value
        )
        self.start_time = time.monotonic()
        self.last_print_time = 0.0
        self.last_message_time = None
        self.waiting_message_printed = False

        LOG_DIR.mkdir(exist_ok=True)
        log_name = datetime.now().strftime("position_log_%Y%m%d_%H%M%S.csv")
        self.log_path = LOG_DIR / log_name
        self.log_file = self.log_path.open("w", newline="", encoding="utf-8")
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

        self.create_subscription(
            Odometry,
            odometry_topic,
            self.odom_callback,
            10,
        )
        self.create_timer(1.0, self.status_callback)

        self.get_logger().info(f"Listening for odometry on {odometry_topic}")
        self.get_logger().info(f"Logging position to {self.log_path}")

    def odom_callback(self, msg):
        now = time.monotonic()
        self.last_message_time = now
        self.waiting_message_printed = False

        if now - self.last_print_time < PRINT_PERIOD_SECONDS:
            return

        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        twist = msg.twist.twist
        yaw_degrees = quaternion_to_yaw_degrees(orientation) 
        wall_time = datetime.now().isoformat(timespec="seconds")
        message_time = stamp_to_seconds(msg.header.stamp)

        print(
            "Odometry | "
            f"x={position.x:.{DECIMAL_PLACES}f} m, "
            f"y={position.y:.{DECIMAL_PLACES}f} m, "
            f"z={position.z:.{DECIMAL_PLACES}f} m, "
            f"yaw={yaw_degrees:.{DECIMAL_PLACES}f} deg, "
            f"vx={twist.linear.x:.{DECIMAL_PLACES}f} m/s, "
            f"wz={twist.angular.z:.{DECIMAL_PLACES}f} rad/s"
        )

        self.csv_writer.writerow([
            wall_time,
            f"{message_time:.9f}",
            msg.header.frame_id,
            msg.child_frame_id,
            f"{position.x:.{DECIMAL_PLACES}f}",
            f"{position.y:.{DECIMAL_PLACES}f}",
            f"{position.z:.{DECIMAL_PLACES}f}",
            f"{yaw_degrees:.{DECIMAL_PLACES}f}",
            f"{twist.linear.x:.{DECIMAL_PLACES}f}",
            f"{twist.angular.z:.{DECIMAL_PLACES}f}",
        ])
        self.log_file.flush()
        self.last_print_time = now

    def status_callback(self):
        now = time.monotonic()
        if self.last_message_time is None:
            elapsed = now - self.start_time
            if elapsed >= ODOMETRY_TIMEOUT_SECONDS and not self.waiting_message_printed:
                # self.get_logger().warn(
                #     "No odometry received yet. Start the launch file with fusion enabled, "
                #     f"or pass -p odometry_topic:={RAW_ODOMETRY_TOPIC}."
                # )
                self.waiting_message_printed = True
            return

        if now - self.last_message_time > ODOMETRY_TIMEOUT_SECONDS:
            self.get_logger().warn(
                f"No odometry received for {ODOMETRY_TIMEOUT_SECONDS:.0f} seconds."
            )
            self.last_message_time = now

    def destroy_node(self):
        if not self.log_file.closed:
            self.log_file.close()
        super().destroy_node()


def main():
    rclpy.init()
    node = PositionPrinter()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
