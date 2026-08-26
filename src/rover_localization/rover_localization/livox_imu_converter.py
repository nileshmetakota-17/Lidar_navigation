#!/usr/bin/env python3

import copy

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu


GRAVITY = 9.80665


class LivoxImuConverter(Node):
    def __init__(self):
        super().__init__('livox_imu_converter')

        self.publisher = self.create_publisher(
            Imu,
            '/livox/imu_si',
            qos_profile_sensor_data,
        )

        self.subscription = self.create_subscription(
            Imu,
            '/livox/imu',
            self.imu_callback,
            qos_profile_sensor_data,
        )

        self.get_logger().info(
            'Converting /livox/imu acceleration from g to m/s^2'
        )

    def imu_callback(self, input_msg):
        output_msg = copy.deepcopy(input_msg)

        # Convert g to m/s²
        output_msg.linear_acceleration.x *= GRAVITY
        output_msg.linear_acceleration.y *= GRAVITY
        output_msg.linear_acceleration.z *= GRAVITY

        # Convert acceleration covariance from g² to (m/s²)².
        covariance_scale = GRAVITY * GRAVITY
        output_msg.linear_acceleration_covariance = [
            value * covariance_scale
            for value in input_msg.linear_acceleration_covariance
        ]

        # Livox does not appear to provide an orientation estimate.
        output_msg.orientation_covariance[0] = -1.0

        self.publisher.publish(output_msg)


def main(args=None):
    rclpy.init(args=args)
    node = LivoxImuConverter()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()