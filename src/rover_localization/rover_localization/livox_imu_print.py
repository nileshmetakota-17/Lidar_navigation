#!/usr/bin/env python3

import math

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu


def wrap_to_pi(angle: float) -> float:
    """Keep an angle between -pi and +pi."""
    return math.atan2(math.sin(angle), math.cos(angle))


class LivoxYawReader(Node):

    def __init__(self) -> None:
        super().__init__('livox_yaw_reader')

        # Number of stationary samples used to estimate gyro Z bias.
        self.calibration_samples = 300
        self.bias_sample_count = 0
        self.gyro_z_bias_sum = 0.0
        self.gyro_z_bias = 0.0
        self.calibrated = False

        # Integrated relative yaw.
        self.yaw = 0.0

        # Previous IMU timestamp.
        self.previous_time = None

        # Limit terminal output to approximately 10 Hz.
        self.last_print_time = None
        self.print_period = 0.1

        self.subscription = self.create_subscription(
            Imu,
            '/livox/imu',
            self.imu_callback,
            qos_profile_sensor_data
        )

        self.get_logger().info('Listening to /livox/imu')
        self.get_logger().info(
            'Keep the robot stationary during gyro calibration.'
        )

    def get_message_time(self, msg: Imu) -> float:
        """Return message time in seconds."""

        stamp = msg.header.stamp

        message_time = (
            float(stamp.sec) +
            float(stamp.nanosec) * 1e-9
        )

        # Use the node clock when the incoming timestamp is zero.
        if message_time == 0.0:
            message_time = self.get_clock().now().nanoseconds * 1e-9

        return message_time

    def calibrate_gyro(self, gyro_z: float) -> None:
        """Estimate stationary Z-axis gyro bias."""

        self.gyro_z_bias_sum += gyro_z
        self.bias_sample_count += 1

        if self.bias_sample_count % 25 == 0:
            print(
                f'\rCalibrating gyro: '
                f'{self.bias_sample_count}/{self.calibration_samples}',
                end='',
                flush=True
            )

        if self.bias_sample_count >= self.calibration_samples:
            self.gyro_z_bias = (
                self.gyro_z_bias_sum /
                float(self.calibration_samples)
            )

            self.calibrated = True
            self.previous_time = None

            print()
            self.get_logger().info(
                f'Calibration complete. '
                f'Gyro Z bias: {self.gyro_z_bias:.8f} rad/s'
            )

    def imu_callback(self, msg: Imu) -> None:
        gyro_z_raw = msg.angular_velocity.z
        current_time = self.get_message_time(msg)

        # First estimate the stationary gyro bias.
        if not self.calibrated:
            self.calibrate_gyro(gyro_z_raw)
            return

        # Initialize integration timestamp.
        if self.previous_time is None:
            self.previous_time = current_time
            return

        dt = current_time - self.previous_time
        self.previous_time = current_time

        # Reject invalid timestamps or large timestamp jumps.
        if dt <= 0.0 or dt > 0.5:
            self.get_logger().warning(
                f'Ignoring invalid IMU time step: {dt:.6f} s'
            )
            return

        # Remove stationary gyro bias.
        gyro_z_corrected = gyro_z_raw - self.gyro_z_bias

        # Integrate angular velocity to obtain relative yaw.
        self.yaw += gyro_z_corrected * dt
        self.yaw = wrap_to_pi(self.yaw)

        # Throttle terminal printing.
        if (
            self.last_print_time is None or
            current_time - self.last_print_time >= self.print_period
        ):
            self.last_print_time = current_time
            self.print_data(
                msg=msg,
                dt=dt,
                gyro_z_raw=gyro_z_raw,
                gyro_z_corrected=gyro_z_corrected
            )

    def print_data(
        self,
        msg: Imu,
        dt: float,
        gyro_z_raw: float,
        gyro_z_corrected: float
    ) -> None:
        yaw_degrees = math.degrees(self.yaw)

        print('\n---------------- Livox IMU ----------------')
        print(f'Frame: {msg.header.frame_id}')
        print(f'dt: {dt:.6f} seconds')

        print('\nGyroscope Z:')
        print(f'  Raw:       {gyro_z_raw:.8f} rad/s')
        print(f'  Bias:      {self.gyro_z_bias:.8f} rad/s')
        print(f'  Corrected: {gyro_z_corrected:.8f} rad/s')

        print('\nIntegrated relative yaw:')
        print(f'  Radians: {self.yaw:.6f}')
        print(f'  Degrees: {yaw_degrees:.3f}')

        print('\nAngular velocity [rad/s]:')
        print(f'  x: {msg.angular_velocity.x:.6f}')
        print(f'  y: {msg.angular_velocity.y:.6f}')
        print(f'  z: {msg.angular_velocity.z:.6f}')

        print('\nLinear acceleration:')
        print(f'  x: {msg.linear_acceleration.x:.6f}')
        print(f'  y: {msg.linear_acceleration.y:.6f}')
        print(f'  z: {msg.linear_acceleration.z:.6f}')


def main(args=None) -> None:
    rclpy.init(args=args)

    node = LivoxYawReader()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\nStopping Livox IMU reader.')
    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()