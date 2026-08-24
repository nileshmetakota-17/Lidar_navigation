#!/usr/bin/env python3

import math
import os

import rclpy
import yaml
from sensor_msgs.msg import Imu
import time


next_print_time = time.monotonic()

NODE_NAME = "print_imu_node"
IMU_TOPIC = "/imu/data"
SUBSCRIPTION_QUEUE_SIZE = 30
DECIMAL_PLACES = 3
PRINT_PREFIX = "IMU"


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


def imu_callback(msg):
    global next_print_time

    now = time.monotonic()

    if now < next_print_time:
        return
    # yaw_degrees = quaternion_to_yaw_degrees(msg.orientation)
    # heading = math.radians(float(packet["imu_heading"]))
    print(  
        f"{PRINT_PREFIX} - "
        f"frame: {msg.header.frame_id}, "
        # f"yaw: {msg.imu_heading:.{DECIMAL_PLACES}f} deg, "
        f"gyro_z: {msg.angular_velocity.z:.{DECIMAL_PLACES}f} rad/s, "
        f"accel_x: {msg.linear_acceleration.x:.{DECIMAL_PLACES}f} m/s^2, "
        f"accel_y: {msg.linear_acceleration.y:.{DECIMAL_PLACES}f} m/s^2, "
        f"accel_z: {msg.linear_acceleration.z:.{DECIMAL_PLACES}f} m/s^2"
    )

    next_print_time = now + 1.0

def main():
    rclpy.init()
    node = rclpy.create_node(NODE_NAME)
    node.get_logger().info(f"Listening for IMU on {IMU_TOPIC}")
    node.create_subscription(
        Imu,
        IMU_TOPIC,
        imu_callback,
        SUBSCRIPTION_QUEUE_SIZE,
    )

    node.get_logger().info("Node ready")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
