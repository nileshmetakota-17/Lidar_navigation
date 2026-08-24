#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node

from geometry_msgs.msg import Twist
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool


DEFAULT_JOY_TOPIC = "/joy"
DEFAULT_CMD_VEL_TOPIC = "/cmd_vel_joy"
MIN_PUBLISH_RATE = 1.0
STOP_EPSILON = 0.001


class SonyJoyRoverTeleop(Node):
    def __init__(self):
        super().__init__("sony_joy_rover_teleop")

        # Topics
        self.declare_parameter("joy_topic", DEFAULT_JOY_TOPIC)
        self.declare_parameter("cmd_vel_topic", DEFAULT_CMD_VEL_TOPIC)

        # Sony / PlayStation controller defaults.
        # You may need to change these after checking: ros2 topic echo /joy
        self.declare_parameter("axis_linear", 1)       # usually left stick up/down
        self.declare_parameter("axis_angular", 3)      # usually left stick left/right

        self.declare_parameter("invert_linear", False)
        self.declare_parameter("invert_angular", False)

        # Speed limits
        self.declare_parameter("scale_linear", 0.3)
        self.declare_parameter("scale_angular", 0.5)
        self.declare_parameter("turbo_scale", 2.0)

        # Proportional smoothing. Larger values react and stop faster; smaller
        # values produce a gentler acceleration/deceleration ramp.
        self.declare_parameter("linear_kp", 1.0)
        self.declare_parameter("angular_kp", 3.0)

        # Buttons
        # Set require_enable=True if you want to hold a button to move.
        self.declare_parameter("require_enable", False)
        self.declare_parameter("enable_button", 5)     # often R1, but check /joy
        self.declare_parameter("turbo_button", 7)      # often R2 / Options depending mapping
        self.declare_parameter("stop_button", 0)
        self.declare_parameter("solo_button", 1)
        self.declare_parameter("temporary_button", 2)

        # Safety
        self.declare_parameter("deadzone", 0.08)
        self.declare_parameter("publish_rate", 50.0)
        self.declare_parameter("joy_timeout", 0.5)
        self.declare_parameter("debug_joy", False)
        self.declare_parameter("debug_rate", 2.0)

        self.joy_topic = self.get_parameter("joy_topic").value
        self.cmd_vel_topic = self.get_parameter("cmd_vel_topic").value

        self.axis_linear = int(self.get_parameter("axis_linear").value)
        self.axis_angular = int(self.get_parameter("axis_angular").value)

        self.invert_linear = bool(self.get_parameter("invert_linear").value)
        self.invert_angular = bool(self.get_parameter("invert_angular").value)

        self.scale_linear = float(self.get_parameter("scale_linear").value)
        self.scale_angular = float(self.get_parameter("scale_angular").value)
        self.turbo_scale = float(self.get_parameter("turbo_scale").value)
        self.linear_kp = max(
            0.1,
            float(self.get_parameter("linear_kp").value),
        )
        self.angular_kp = max(
            0.1,
            float(self.get_parameter("angular_kp").value),
        )

        self.require_enable = bool(self.get_parameter("require_enable").value)
        self.enable_button = int(self.get_parameter("enable_button").value)
        self.turbo_button = int(self.get_parameter("turbo_button").value)
        self.stop_button = int(self.get_parameter("stop_button").value)
        self.solo_button = int(self.get_parameter("solo_button").value)
        self.temporary_button = int(
            self.get_parameter("temporary_button").value
        )

        self.deadzone = self.clamp(
            float(self.get_parameter("deadzone").value),
            0.0,
            1.0,
        )
        self.joy_timeout = max(0.0, float(self.get_parameter("joy_timeout").value))
        self.debug_joy = bool(self.get_parameter("debug_joy").value)
        self.debug_period = 1.0 / max(
            MIN_PUBLISH_RATE,
            float(self.get_parameter("debug_rate").value),
        )

        publish_rate = max(
            MIN_PUBLISH_RATE,
            float(self.get_parameter("publish_rate").value),
        )

        self.last_joy_msg = None
        self.last_joy_time = 0.0
        self.last_debug_time = 0.0
        self.connected = False
        self.last_axes_count = None
        self.last_buttons_count = None
        self.current_linear = 0.0
        self.current_angular = 0.0
        self.last_publish_time = time.monotonic()
        self.enable_was_active = False
        self.solo_mode = False
        self.solo_button_was_pressed = False
        self.temporary_button_was_pressed = False

        self.pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        self.solo_lock_pub = self.create_publisher(
            Bool,
            "/joystick_solo_lock",
            10,
        )
        self.sub = self.create_subscription(
            Joy,
            self.joy_topic,
            self.joy_callback,
            10,
        )

        self.timer = self.create_timer(1.0 / publish_rate, self.publish_cmd)

        self.get_logger().info("Sony joystick rover teleop started.")
        self.get_logger().info(f"Subscribing to: {self.joy_topic}")
        self.get_logger().info(f"Publishing to:  {self.cmd_vel_topic}")
        self.get_logger().info(
            f"axis_linear={self.axis_linear}, axis_angular={self.axis_angular}"
        )
        self.get_logger().info(
            f"stop_button={self.stop_button}, turbo_button={self.turbo_button}"
        )
        self.get_logger().info(
            f"solo_button={self.solo_button}, "
            f"temporary_button={self.temporary_button}"
        )
        self.get_logger().info(
            f"command smoothing: linear_kp={self.linear_kp:.2f}, "
            f"angular_kp={self.angular_kp:.2f}"
        )
        if self.require_enable:
            self.get_logger().info(f"Enable button required: {self.enable_button}")
        if self.debug_joy:
            self.get_logger().info(
                "Joystick debug enabled: move sticks / press buttons to see "
                "axes and button bindings."
            )

    def joy_callback(self, msg: Joy):
        self.last_joy_msg = msg
        self.last_joy_time = time.monotonic()
        self.report_connection(msg)

    def report_connection(self, msg: Joy):
        axes_count = len(msg.axes)
        buttons_count = len(msg.buttons)
        if (
            self.connected
            and self.last_axes_count == axes_count
            and self.last_buttons_count == buttons_count
        ):
            return

        self.connected = True
        self.last_axes_count = axes_count
        self.last_buttons_count = buttons_count
        self.get_logger().info(
            f"Joystick connected on {self.joy_topic}: "
            f"{axes_count} axes, {buttons_count} buttons."
        )
        self.get_logger().info(
            "Current drive binding: "
            f"linear axis {self.axis_linear}, angular axis {self.axis_angular}, "
            f"stop button {self.stop_button}, turbo button {self.turbo_button}."
        )

    @staticmethod
    def clamp(value: float, min_value: float, max_value: float) -> float:
        return min(max(value, min_value), max_value)

    def get_axis(self, msg: Joy, index: int) -> float:
        if index < 0 or index >= len(msg.axes):
            self.get_logger().warn(
                f"Joystick axis index {index} is outside received axes.",
                throttle_duration_sec=5.0,
            )
            return 0.0
        value = float(msg.axes[index])

        if abs(value) < self.deadzone:
            return 0.0

        return value

    def get_button(self, msg: Joy, index: int) -> bool:
        if index < 0 or index >= len(msg.buttons):
            self.get_logger().warn(
                f"Joystick button index {index} is outside received buttons.",
                throttle_duration_sec=5.0,
            )
            return False
        return msg.buttons[index] == 1

    def stop_rover(self):
        self.current_linear = 0.0
        self.current_angular = 0.0
        self.pub.publish(Twist())

    def stop_once_and_release(self):
        """Stop once, then become silent so lower-priority inputs can run."""
        self.current_linear = 0.0
        self.current_angular = 0.0
        if self.enable_was_active:
            self.pub.publish(Twist())
        self.enable_was_active = False

    def update_control_mode(self, joy: Joy):
        solo_pressed = self.get_button(joy, self.solo_button)
        temporary_pressed = self.get_button(joy, self.temporary_button)

        if solo_pressed and not self.solo_button_was_pressed:
            self.solo_mode = True
            self.get_logger().warn("Joystick SOLO mode enabled.")
        if temporary_pressed and not self.temporary_button_was_pressed:
            self.solo_mode = False
            self.get_logger().info("Temporary manual override mode enabled.")

        self.solo_button_was_pressed = solo_pressed
        self.temporary_button_was_pressed = temporary_pressed
        self.solo_lock_pub.publish(Bool(data=self.solo_mode))

    @staticmethod
    def smooth_command(current: float, target: float, kp: float, dt: float) -> float:
        """Move a command proportionally toward its target."""
        alpha = min(1.0, max(0.0, kp * dt))
        value = current + alpha * (target - current)

        if target == 0.0 and abs(value) < STOP_EPSILON:
            return 0.0

        return value

    def debug_inputs(
        self,
        joy: Joy,
        linear_input: float,
        angular_input: float,
        twist: Twist,
        now: float,
    ):
        if not self.debug_joy or now - self.last_debug_time < self.debug_period:
            return

        self.last_debug_time = now
        axes = [round(axis, 3) for axis in joy.axes]
        active_buttons = [
            index for index, pressed in enumerate(joy.buttons) if pressed == 1
        ]
        self.get_logger().info(
            "joy debug: "
            f"axes={axes} active_buttons={active_buttons} | "
            f"linear_axis[{self.axis_linear}]={linear_input:.3f}, "
            f"angular_axis[{self.axis_angular}]={angular_input:.3f} -> "
            f"cmd linear.x={twist.linear.x:.3f}, "
            f"angular.z={twist.angular.z:.3f}"
        )

    def publish_cmd(self):
        now = time.monotonic()
        dt = min(0.1, max(0.0, now - self.last_publish_time))
        self.last_publish_time = now

        if self.last_joy_msg is None:
            self.get_logger().warn(
                f"No Joy messages received on {self.joy_topic}. "
                "Start joy_node or check ROS_DOMAIN_ID.",
                throttle_duration_sec=5.0,
            )
            self.stop_once_and_release()
            return

        if now - self.last_joy_time > self.joy_timeout:
            if self.connected:
                self.connected = False
            self.get_logger().warn(
                f"Joy input timed out after {self.joy_timeout:.2f}s.",
                throttle_duration_sec=5.0,
            )
            self.stop_once_and_release()
            return

        joy = self.last_joy_msg
        self.update_control_mode(joy)

        if self.get_button(joy, self.stop_button):
            self.stop_rover()
            return

        if (
            self.require_enable
            and not self.solo_mode
            and not self.get_button(joy, self.enable_button)
        ):
            self.stop_once_and_release()
            return

        self.enable_was_active = True

        linear_input = self.get_axis(joy, self.axis_linear)
        angular_input = self.get_axis(joy, self.axis_angular)

        if self.invert_linear:
            linear_input *= -1.0

        if self.invert_angular:
            angular_input *= -1.0

        speed_multiplier = 1.0
        if self.get_button(joy, self.turbo_button):
            speed_multiplier = self.turbo_scale

        target_linear = linear_input * self.scale_linear * speed_multiplier
        target_angular = angular_input * self.scale_angular * speed_multiplier

        self.current_linear = self.smooth_command(
            self.current_linear,
            target_linear,
            self.linear_kp,
            dt,
        )
        self.current_angular = self.smooth_command(
            self.current_angular,
            target_angular,
            self.angular_kp,
            dt,
        )

        twist = Twist()
        twist.linear.x = self.current_linear
        twist.angular.z = self.current_angular

        self.debug_inputs(joy, linear_input, angular_input, twist, now)
        self.pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)

    node = SonyJoyRoverTeleop()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_rover()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
