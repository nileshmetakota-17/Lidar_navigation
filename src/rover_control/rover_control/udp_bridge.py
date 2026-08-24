import ast
import math
import socket
import json
import time 

import rclpy
from rclpy.node import Node

from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu, JointState
from tf2_ros import TransformBroadcaster
from geometry_msgs.msg import TransformStamped
from geometry_msgs.msg import Twist

#from tf_transformations import quaternion_from_euler

def quaternion_to_euler(x, y, z, w):

	sinr_cosp = 2 * (w * x + y * z)
	cosr_cosp = 1 - 2 * (x * x + y * y)
	roll = math.atan2(sinr_cosp, cosr_cosp)

	sinp = 2 * (w * y - z * x)
	if abs(sinp) >= 1:
		pitch = math.copysign(math.pi / 2, sinp)
	else:
		pitch = math.asin(sinp)

	siny_cosp = 2 * (w * z + x * y)
	cosy_cosp = 1 - 2 * (y * y + z * z)
	yaw = math.atan2(siny_cosp, cosy_cosp)

	return roll, pitch, yaw

def euler_to_quaternion(roll, pitch, yaw):

	cy = math.cos(yaw * 0.5)
	sy = math.sin(yaw * 0.5)

	cp = math.cos(pitch * 0.5)
	sp = math.sin(pitch * 0.5)

	cr = math.cos(roll * 0.5)
	sr = math.sin(roll * 0.5)

	qw = cr * cp * cy + sr * sp * sy
	qx = sr * cp * cy - cr * sp * sy
	qy = cr * sp * cy + sr * cp * sy
	qz = cr * cp * sy - sr * sp * cy

	return qx, qy, qz, qw

class UDPBridge(Node):

	def __init__(self):
		super().__init__('udp_bridge')
		
		self.odom_pub = self.create_publisher(Odometry,'/odom',10)
		self.imu_pub = self.create_publisher(Imu,'/imu/data',10)
		self.joint_state_pub = self.create_publisher(JointState, '/joint_states', 10)

		# Physical differential-drive dimensions.
		self.declare_parameter('wheel_radius', 0.07305)
		self.declare_parameter('wheel_separation', 0.291)
		self.wheel_radius = self.get_parameter('wheel_radius').value
		self.wheel_separation = self.get_parameter('wheel_separation').value
		self.left_wheel_position = 0.0
		self.right_wheel_position = 0.0
		self.last_joint_time = None
		self.sock = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
		self.sock.bind(("0.0.0.0",5000))
		self.sock.setblocking(False)
		
		self.timer = self.create_timer(0.01,self.read_udp)
		
		self.last_packet_print_time = 0.0
		self.packet_print_period = 1.0

		self.get_logger().info("UDP Bridge Started...")
		self.tf_broadcaster = TransformBroadcaster(self)
		
		self.pi_ip = "192.168.10.2"
		self.pi_port = 5006
		
		# Teleop
		self.cmd_vel_sub = self.create_subscription(Twist,"/cmd_vel",self.cmd_vel_callback,10)
		
	def cmd_vel_callback(self, msg):
		packet = {
			"linear": msg.linear.x,
			"angular": msg.angular.z
		}
		
		self.sock.sendto(
			json.dumps(packet).encode(),
			(self.pi_ip, self.pi_port)
		)
		
	def read_udp(self):
		try:
			data, addr = self.sock.recvfrom(4096)

		except BlockingIOError:
			return

		except OSError as error:
			self.get_logger().error(
				f"UDP receive error: {error}"
			)
			return

		try:
			decoded_data = data.decode("utf-8")

			# Try JSON first.
			try:
				packet = json.loads(decoded_data)

			# Fall back to a Python dictionary string.
			except json.JSONDecodeError:
				packet = ast.literal_eval(decoded_data)

		except (
			UnicodeDecodeError,
			ValueError,
			SyntaxError,
		) as error:
			self.get_logger().error(
				f"Invalid UDP packet: {error}"
			)
			return

		if not isinstance(packet, dict):
			self.get_logger().error(
				f"Expected dictionary, received "
				f"{type(packet).__name__}"
			)
			return

		# Print only once every second.
		current_time = time.monotonic()

		if (
			current_time - self.last_packet_print_time
			>= self.packet_print_period
		):
			self.get_logger().info(
				"UDP packet received from "
				f"{addr[0]}:{addr[1]}\n"
				f"{json.dumps(packet, indent=2)}"
			)

			self.last_packet_print_time = current_time

		# These still run for every received packet.
		try:
			self.publish_odom(packet)
			self.publish_imu(packet)
			self.publish_joint_states(packet)

		except KeyError as error:
			self.get_logger().error(
				f"Required packet field is missing: {error}"
			)

		except (TypeError, ValueError) as error:
			self.get_logger().error(
				f"Invalid packet value: {error}"
			)
		
	def publish_odom(self, packet):
	
		msg = Odometry()
		
		msg.header.stamp = self.get_clock().now().to_msg()
		msg.header.frame_id = "odom"
		msg.child_frame_id = "base_link"
		
		msg.pose.pose.position.x = packet["odom_x"]
		msg.pose.pose.position.y = packet["odom_y"]
		msg.pose.pose.position.z = 0.0
		
		'''
		q = quaternion_from_euler(
		0.0,
		0.0,
		packet["odom_theta"]
		)
		
		msg.pose.pose.orientation.x = q[0]
		msg.pose.pose.orientation.y = q[1]
		msg.pose.pose.orientation.z = q[2]
		msg.pose.pose.orientation.w = q[3]
		'''
		
		theta = packet["odom_theta"]
		
		msg.pose.pose.orientation.x = 0.0
		msg.pose.pose.orientation.y = 0.0
		msg.pose.pose.orientation.z = math.sin(theta/2.0)
		msg.pose.pose.orientation.w = math.cos(theta/2.0)

		msg.twist.twist.linear.x = (packet["odom_linear_velocity"])
		msg.twist.twist.angular.z = (packet["odom_angular_velocity"])
		
		self.odom_pub.publish(msg)

	def publish_joint_states(self, packet):
		now = self.get_clock().now()

		if self.last_joint_time is None:
			self.last_joint_time = now
			return

		dt = (now - self.last_joint_time).nanoseconds * 1e-9
		self.last_joint_time = now

		# Ignore invalid or abnormally long gaps between UDP packets.
		if dt <= 0.0 or dt > 1.0:
			return

		linear = float(packet['odom_linear_velocity'])
		angular = float(packet['odom_angular_velocity'])

		left_linear = linear - angular * self.wheel_separation / 2.0
		right_linear = linear + angular * self.wheel_separation / 2.0

		left_wheel_velocity = left_linear / self.wheel_radius
		right_wheel_velocity = right_linear / self.wheel_radius

		# The URDF axes are -Y for the left joint and +Y for the right joint.
		left_joint_velocity = -left_wheel_velocity
		right_joint_velocity = right_wheel_velocity

		self.left_wheel_position += left_joint_velocity * dt
		self.right_wheel_position += right_joint_velocity * dt

		msg = JointState()
		msg.header.stamp = now.to_msg()
		msg.name = [
			'LWheel_Joint',
			'RWheel_Joint',
			'Castermock_Joint',
			'Caster_Joint',
		]
		msg.position = [
			self.left_wheel_position,
			self.right_wheel_position,
			0.0,
			0.0,
		]
		msg.velocity = [
			left_joint_velocity,
			right_joint_velocity,
			0.0,
			0.0,
		]
		self.joint_state_pub.publish(msg)
		
	def publish_imu(self, packet):
		
		msg = Imu()
		
		msg.header.stamp = self.get_clock().now().to_msg()
		msg.header.frame_id = "imu_link"
		
		
		msg.orientation.x = packet["qx"]
		msg.orientation.y = packet["qy"]
		msg.orientation.z = packet["qz"]
		msg.orientation.w = packet["qw"]

		#roll, pitch, yaw = quaternion_to_euler(packet["qx"],packet["qy"],packet["qz"],packet["qw"])
		
		
		#roll_ros = roll - math.pi
		#while roll_ros > math.pi:
		#	roll_ros -= 2 * math.pi

		#while roll_ros < -math.pi:
		#	roll_ros += 2 * math.pi
		#pitch_ros = -pitch
		#yaw_ros = -yaw #+ math.pi/2
		
		#qx, qy, qz, qw = euler_to_quaternion(roll_ros, pitch_ros, yaw_ros)
		
		'''
		self.get_logger().info(
			f"r={math.degrees(roll_ros):.1f}, "
			f"p={math.degrees(pitch_ros):.1f}, "
			f"y={math.degrees(yaw_ros):.1f}"
		)
		'''

		#msg.orientation.x = qx
		#msg.orientation.y = qy
		#msg.orientation.z = qz
		#msg.orientation.w = qw
		
		msg.angular_velocity.x = packet["gyro_x"]
		msg.angular_velocity.y = packet["gyro_y"]
		msg.angular_velocity.z = packet["gyro_z"]

		msg.linear_acceleration.x = packet["imu_accel_x"]
		msg.linear_acceleration.y = packet["imu_accel_y"]
		msg.linear_acceleration.z = packet["imu_accel_z"]
		
		self.imu_pub.publish(msg)
	
	def publish_tf(self, packet):
	
		t = TransformStamped()
		
		t.header.stamp = self.get_clock().now().to_msg()
		
		t.header.frame_id = "odom"
		t.child_frame_id = "base_link"
		
		t.transform.translation.x = packet["odom_x"]
		t.transform.translation.y = packet["odom_y"]
		t.transform.translation.z = 0.0

		theta = packet["odom_theta"]

		
		t.transform.rotation.x = 0.0
		t.transform.rotation.y = 0.0
		t.transform.rotation.z = math.sin(theta/2.0)
		t.transform.rotation.w = math.cos(theta/2.0)
		
		self.tf_broadcaster.sendTransform(t)
		
		
def main(args=None):
	rclpy.init(args=args)
	node = UDPBridge()
	rclpy.spin(node)
	node.destroy_node()
	rclpy.shutdown()
	
if __name__ == "__main__":
	main()
