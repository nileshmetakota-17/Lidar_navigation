#!/usr/bin/env python3

import math

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry, Path
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy


# Default odometry source: fused estimate from robot_localization EKF.
DEFAULT_ODOMETRY_TOPIC = "/odometry/filtered"

# Default path topic (override per node in launch).
DEFAULT_PATH_TOPIC = "/model/rover/path_fused"

# Node name shown in `ros2 node list`.
NODE_NAME = "odom_to_path_node"

# Minimum travel between stored points. Skips duplicate poses when the rover is still.
MIN_POINT_DISTANCE_M = 0.005

# How often the full path is republished to RViz (seconds). Keeps the trail visible in RViz.
PUBLISH_PERIOD_S = 0.05

# Keeps the latest path available for RViz even if it subscribes after the first update.
PATH_QOS = QoSProfile(
    depth=10,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    reliability=ReliabilityPolicy.RELIABLE,
)


class OdomToPath(Node):
    def __init__(self):
        super().__init__(NODE_NAME)
        self.declare_parameter("odometry_topic", DEFAULT_ODOMETRY_TOPIC)
        self.declare_parameter("path_topic", DEFAULT_PATH_TOPIC)
        self.declare_parameter("minimum_point_distance", MIN_POINT_DISTANCE_M)
        self.declare_parameter("publish_period", PUBLISH_PERIOD_S)
        odometry_topic = self.get_parameter("odometry_topic").get_parameter_value().string_value
        path_topic = self.get_parameter("path_topic").get_parameter_value().string_value
        self.minimum_point_distance = float(
            self.get_parameter("minimum_point_distance").value
        )
        publish_period = float(self.get_parameter("publish_period").value)
        # Full driven path kept in memory until this node stops (when launch / RViz session ends).
        self.poses = []
        self.publisher = self.create_publisher(Path, path_topic, PATH_QOS)
        self.create_subscription(Odometry, odometry_topic, self.odom_callback, 10)
        self.create_timer(publish_period, self._republish_path)
        self.get_logger().info(
            f"Publishing path on {path_topic} from {odometry_topic} "
            "(kept until launch stops)"
        )

    def _publish_path(self):
        path = Path()
        path.header.frame_id = "odom"
        # Use the node clock so Path stamps always move forward in sim time.
        path.header.stamp = self.get_clock().now().to_msg()
        path.poses = list(self.poses)
        self.publisher.publish(path)

    def _republish_path(self):
        if self.poses:
            self._publish_path()

    def _should_add_pose(self, pose):
        if not self.poses:
            return True

        last_pose = self.poses[-1].pose.position
        dx = pose.pose.position.x - last_pose.x
        dy = pose.pose.position.y - last_pose.y
        return math.hypot(dx, dy) >= self.minimum_point_distance

    def odom_callback(self, msg):
        pose = PoseStamped()
        pose.header = msg.header
        pose.pose = msg.pose.pose

        if not self._should_add_pose(pose):
            return

        self.poses.append(pose)

        # The timer publishes at a stable rate; callbacks only collect poses.


def main():
    rclpy.init()
    node = OdomToPath()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
