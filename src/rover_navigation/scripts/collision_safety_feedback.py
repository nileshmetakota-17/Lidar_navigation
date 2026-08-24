#!/usr/bin/env python3
"""Publish human-readable feedback for collision-filtered Nav2 commands."""

import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import String
from visualization_msgs.msg import Marker


class CollisionSafetyFeedback(Node):
    def __init__(self):
        super().__init__("collision_safety_feedback")
        self.input_cmd = Twist()
        self.safe_cmd = Twist()
        self.last_input_time = None
        self.last_safe_time = None
        self.status = "IDLE"
        self.create_subscription(
            Twist, "/cmd_vel_nav_smoothed", self._input_callback, 10
        )
        self.create_subscription(Twist, "/cmd_vel_nav_safe", self._safe_callback, 10)
        self.status_pub = self.create_publisher(String, "/collision_safety_status", 10)
        self.marker_pub = self.create_publisher(
            Marker, "/collision_safety_marker", 10
        )
        self.create_timer(0.1, self._publish_status)

    @staticmethod
    def _magnitude(msg):
        return math.hypot(msg.linear.x, msg.angular.z)

    def _input_callback(self, msg):
        self.input_cmd = msg
        self.last_input_time = self.get_clock().now()

    def _safe_callback(self, msg):
        self.safe_cmd = msg
        self.last_safe_time = self.get_clock().now()

    def _publish_status(self):
        now = self.get_clock().now()
        input_fresh = (
            self.last_input_time is not None
            and (now - self.last_input_time).nanoseconds < 500_000_000
        )
        safe_fresh = (
            self.last_safe_time is not None
            and (now - self.last_safe_time).nanoseconds < 500_000_000
        )

        requested = self._magnitude(self.input_cmd) if input_fresh else 0.0
        permitted = self._magnitude(self.safe_cmd) if safe_fresh else 0.0

        if not input_fresh:
            status = "IDLE"
            color = (0.65, 0.65, 0.65)
        elif requested > 0.01 and permitted < 0.005:
            status = "SAFE STOP"
            color = (1.0, 0.05, 0.05)
        elif requested > 0.01 and permitted < requested * 0.75:
            status = "SLOWDOWN"
            color = (1.0, 0.65, 0.0)
        else:
            status = "CLEAR"
            color = (0.05, 1.0, 0.15)

        if status != self.status:
            self.get_logger().info("Collision safety status: %s" % status)
            self.status = status

        self.status_pub.publish(String(data=status))

        marker = Marker()
        marker.header.stamp = self.get_clock().now().to_msg()
        marker.header.frame_id = "base_link"
        marker.ns = "collision_safety"
        marker.id = 0
        marker.type = Marker.TEXT_VIEW_FACING
        marker.action = Marker.ADD
        marker.pose.position.z = 0.80
        marker.pose.orientation.w = 1.0
        marker.scale.z = 0.16
        marker.color.r, marker.color.g, marker.color.b = color
        marker.color.a = 1.0
        marker.text = status
        marker.lifetime.sec = 0
        self.marker_pub.publish(marker)


def main(args=None):
    rclpy.init(args=args)
    node = CollisionSafetyFeedback()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
