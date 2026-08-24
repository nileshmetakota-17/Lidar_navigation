#!/usr/bin/env python
import math
import os
import rclpy

from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool

import sys, select, termios, time, tty

settings = None
keyboard_input = None
keyboard_solo_lock_pub = None
DEFAULT_CMD_VEL_TOPIC = "/cmd_vel_keyboard"
DEFAULT_ODOMETRY_TOPIC = "/odom"
# RAW_ODOMETRY_TOPIC = ""
STEP_DISTANCE = 0.5
TURN_ANGLE = math.radians(20.0)

# Proportional motion control: move quickly when far from the target and
# reduce speed as the remaining distance/angle becomes smaller.
LINEAR_KP = 1.5
ANGULAR_KP = 1.5
MIN_LINEAR_SPEED = 0.06
MIN_ANGULAR_SPEED = 0.08
DISTANCE_TOLERANCE = 0.01
ANGLE_TOLERANCE = math.radians(1.0)

CONTROL_PERIOD = 0.02
MAX_MOTION_TIME = 3.0
ODOMETRY_WAIT_TIMEOUT = 5.0

current_x = None
current_y = None
current_yaw = None

msg = """
Reading from the keyboard  and Publishing to Twist!
---------------------------
Arrow keys:
   Up / Down    : forward / backward
   Left / Right : turn left / turn right

q/z : increase/decrease max speeds by 10%
w/x : increase/decrease only linear speed by 10%
e/c : increase/decrease only angular speed by 10%

Space : stop
0    : keyboard solo mode (blocks Nav2)
1     : temporary override mode (Nav2 resumes)
CTRL-C to quit
"""



moveBindings = {
		'\x1b[A':(1,0,0,0),
		'\x1bOA':(1,0,0,0),
		'\x1b[D':(0,0,0,1),
		'\x1bOD':(0,0,0,1),
		'\x1b[C':(0,0,0,-1),
		'\x1bOC':(0,0,0,-1),
		'\x1b[B':(-1,0,0,0),
		'\x1bOB':(-1,0,0,0),
	       }

speedBindings={
		'q':(1.1,1.1),
		'z':(.9,.9),
		'w':(1.1,1),
		'x':(.9,1),
		'e':(1,1.1),
		'c':(1,.9),
	      }

arrowBindings = {
		'A':'\x1b[A',
		'B':'\x1b[B',
		'C':'\x1b[C',
		'D':'\x1b[D',
	      }

def normalizeKey(key):
	if key.startswith('\x1b') and key[-1:] in arrowBindings:
		return arrowBindings[key[-1:]]
	return key

def readKey(timeout=None):
	fd = keyboard_input.fileno()
	if timeout is not None:
		ready, _, _ = select.select([fd], [], [], timeout)
		if not ready:
			return None

	key = os.read(fd, 1).decode("utf-8", errors="ignore")
	if key == '\x1b':
		end_time = time.time() + 0.25
		while len(key) < 8:
			remaining = end_time - time.time()
			if remaining <= 0:
				break
			ready, _, _ = select.select([fd], [], [], remaining)
			if not ready:
				break
			key += os.read(fd, 8 - len(key)).decode("utf-8", errors="ignore")
			if key[-1:] in arrowBindings:
				break
	return normalizeKey(key)


def getKey():
	return readKey()


def vels(speed,turn):
	return "currently:\tspeed %s\tturn %s " % (speed,turn)

def normalizeAngle(angle):
	return math.atan2(math.sin(angle), math.cos(angle))

def clamp(value, minimum, maximum):
	return max(minimum, min(maximum, value))

def quaternionToYaw(orientation):
	siny_cosp = 2.0 * (
		orientation.w * orientation.z +
		orientation.x * orientation.y
	)
	cosy_cosp = 1.0 - 2.0 * (
		orientation.y * orientation.y +
		orientation.z * orientation.z
	)
	return math.atan2(siny_cosp, cosy_cosp)

def odomCallback(msg):
	global current_x, current_y, current_yaw
	current_x = msg.pose.pose.position.x
	current_y = msg.pose.pose.position.y
	current_yaw = quaternionToYaw(msg.pose.pose.orientation)

def makeTwist(x=0, y=0, z=0, th=0, speed=0.0, turn=0.0):
	twist = Twist()
	twist.linear.x = x*speed; twist.linear.y = y*speed; twist.linear.z = z*speed
	twist.angular.x = 0.0; twist.angular.y = 0.0; twist.angular.z = th*turn
	return twist

def distanceFrom(start_x, start_y):
	return math.hypot(current_x - start_x, current_y - start_y)

def setKeyboardSoloMode(enabled):
	keyboard_solo_lock_pub.publish(Bool(data=enabled))
	if enabled:
		print("Keyboard SOLO mode enabled")
	else:
		print("Temporary manual override mode enabled")

def waitForOdometry(node, odometry_topic, cmd_vel_topic):
	print("Waiting for odometry on %s..." % odometry_topic)
	start_time = time.time()
	while rclpy.ok() and (current_x is None or current_y is None or current_yaw is None):
		rclpy.spin_once(node, timeout_sec=0.1)
		if time.time() - start_time > ODOMETRY_WAIT_TIMEOUT:
			print("")
			print("No odometry received.")
			print("Start the sim launch first (wait until rover spawns, ~5 s):")
			# print("  export ROS_DOMAIN_ID=77")
			# print("  ros2 launch main_rover urdf_assem_gazebo.launch.py")
			print("")
			if odometry_topic == DEFAULT_ODOMETRY_TOPIC:
				print("If fusion is disabled, pass:")
				# print("  --ros-args -p odometry_topic:=%s" % RAW_ODOMETRY_TOPIC)
				print("")
			print("Teleop uses %s and %s." % (odometry_topic, cmd_vel_topic))
			return False
	print("Odometry ready.")
	return True

def executeMotion(node, pub, x, y, z, th, speed, turn):
	if current_x is None or current_y is None or current_yaw is None:
		print("No odometry received yet. Cannot move by distance.")
		return

	start_time = time.time()

	if x != 0:
		start_x = current_x
		start_y = current_y
		while rclpy.ok():
			key = readKey(CONTROL_PERIOD)
			if key in (' ', '\x03'):
				print("Emergency stop")
				break
			if key == '1':
				setKeyboardSoloMode(True)
			elif key == '2':
				setKeyboardSoloMode(False)
			travelled = distanceFrom(start_x, start_y)
			remaining = STEP_DISTANCE - travelled

			if remaining <= DISTANCE_TOLERANCE:
				break

			linear_speed = clamp(
				LINEAR_KP * remaining,
				min(MIN_LINEAR_SPEED, abs(speed)),
				abs(speed),
			)
			pub.publish(makeTwist(x=x, speed=linear_speed))
			rclpy.spin_once(node, timeout_sec=0.0)
			if time.time() - start_time > MAX_MOTION_TIME:
				print("Motion timeout before reaching distance.")
				break
		print("moved distance: %.3f m" % distanceFrom(start_x, start_y))
	elif th != 0:
		start_yaw = current_yaw
		while rclpy.ok():
			key = readKey(CONTROL_PERIOD)
			if key in (' ', '\x03'):
				print("Emergency stop")
				break
			if key == '0':
				setKeyboardSoloMode(True)
			elif key == '1':
				setKeyboardSoloMode(False)
			turned = abs(normalizeAngle(current_yaw - start_yaw))
			remaining = TURN_ANGLE - turned

			if remaining <= ANGLE_TOLERANCE:
				break

			angular_speed = clamp(
				ANGULAR_KP * remaining,
				min(MIN_ANGULAR_SPEED, abs(turn)),
				abs(turn),
			)
			pub.publish(makeTwist(th=th, turn=angular_speed))
			rclpy.spin_once(node, timeout_sec=0.0)
			if time.time() - start_time > MAX_MOTION_TIME:
				print("Motion timeout before reaching turn angle.")
				break
		print("turned angle: %.1f deg" % math.degrees(abs(normalizeAngle(current_yaw - start_yaw))))

	pub.publish(makeTwist())

def main(args=None):	
	global settings, keyboard_input, keyboard_solo_lock_pub

	if args is None:
		args = sys.argv

	# ros2 launch normally replaces stdin with a pipe. Open the controlling
	# terminal explicitly so this interactive node also works from a launch file.
	if sys.stdin.isatty():
		keyboard_input = sys.stdin
	else:
		try:
			keyboard_input = open('/dev/tty', 'r', encoding='utf-8')
		except OSError as error:
			print("Keyboard control needs an interactive terminal: %s" % error)
			print("Run: ros2 run rover_control keyboard_teleop")
			return

	settings = termios.tcgetattr(keyboard_input)
	tty.setraw(keyboard_input.fileno())
	rclpy.init(args=args)
	node = rclpy.create_node('teleop_twist_keyboard')
	node.declare_parameter('odometry_topic', DEFAULT_ODOMETRY_TOPIC)
	node.declare_parameter('cmd_vel_topic', DEFAULT_CMD_VEL_TOPIC)
	odometry_topic = node.get_parameter('odometry_topic').get_parameter_value().string_value
	cmd_vel_topic = node.get_parameter('cmd_vel_topic').get_parameter_value().string_value

	pub = node.create_publisher(Twist, cmd_vel_topic, 10)
	keyboard_solo_lock_pub = node.create_publisher(
		Bool,
		'/keyboard_solo_lock',
		10,
	)
	setKeyboardSoloMode(False)
	node.create_subscription(Odometry, odometry_topic, odomCallback, 10)
	if not waitForOdometry(node, odometry_topic, cmd_vel_topic):
		node.destroy_node()
		rclpy.shutdown()
		return

	speed = 0.5
	turn = 1.0
	status = 0

	try:
		print(msg)
		print(vels(speed,turn))
		while(1):
			key = getKey()
			if key in moveBindings.keys():
				x, y, z, th = moveBindings[key]
				executeMotion(node, pub, x, y, z, th, speed, turn)
			elif key in speedBindings.keys():
				speed = speed * speedBindings[key][0]
				turn = turn * speedBindings[key][1]

				print(vels(speed,turn))
				if (status == 14):
					print(msg)
				status = (status + 1) % 15
			elif key == ' ':
				pub.publish(makeTwist())
			elif key == '1':
				setKeyboardSoloMode(True)
			elif key == '2':
				setKeyboardSoloMode(False)
			else:
				if (key == '\x03'):
					break
				print("unknown key:", repr(key))

	except Exception as e:
		print(e)

	finally:
		pub.publish(makeTwist())

		if settings is not None:
			termios.tcsetattr(keyboard_input, termios.TCSADRAIN, settings)

		if keyboard_input is not sys.stdin:
			keyboard_input.close()

		node.destroy_node()
		rclpy.shutdown()

if __name__ == '__main__':
	main()
