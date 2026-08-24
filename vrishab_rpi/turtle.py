import asyncio
import math
import time
import socket
import json
import moteus
import moteus_pi3hat

from moteus_interface import MoteusInterface, GearReductionDeg
from agv import DifferentialDrive, AngleUnwrapper
# from sensors import MagnetometerRaw
from sub import TeleopSubscriber

def wrap_pi(angle):
	while angle > math.pi:
		angle -= 2.0 * math.pi
	while angle < -math.pi:
		angle += 2.0 * math.pi
	return angle

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

# async def main(vrishab,converter,rover,sock,magnetometer,teleop):
async def main(vrishab,converter,rover,sock,teleop):
	# Clear Moteus_Faults
	await vrishab.disarm()

	# Initializing parameters
	start_time = time.time()
	prev_time = time.time()

	# Initializing async tasks
	# asyncio.create_task(magnetometer.read_mag())
	asyncio.create_task(vrishab.read_motor_states())
	asyncio.create_task(vrishab.imu())
	asyncio.create_task(teleop.receiver())

	while True:
		# Odometry
		current_time = time.time()
		elapsed_time = current_time - start_time

		delta_t = current_time-prev_time
		prev_time = current_time

		states = vrishab.get_states()
		left_wheel_velocity = -math.radians(converter.mot2deg(states["left_vel"]))
		right_wheel_velocity = math.radians(converter.mot2deg(states["right_vel"]))
		position_x, position_y, heading, lin_v_vel, ang_v_vel = rover.wheel_odometry(
			left_wheel_velocity,right_wheel_velocity,delta_t
		)
		#print(f"x = {position_x},y = {position_y}, yaw = {heading}")

		# Imu
		imu_rate, imu_euler_rad, imu_quaternion, imu_accel_mps2 = vrishab.get_imu()
		# Quaternion
		q_w,q_x,q_y,q_z = imu_quaternion["w"], imu_quaternion["x"], imu_quaternion["y"], imu_quaternion["z"]
		# gyro
		roll_rate, pitch_rate, yaw_rate = imu_rate["roll_rate"], imu_rate["pitch_rate"], imu_rate["yaw_rate"]
		#print(f"Rr={roll_rate},pr={pitch_rate},yr={yaw_rate}")
		# accel
		accel_x,accel_y,accel_z = imu_accel_mps2["x"], imu_accel_mps2["y"], imu_accel_mps2["z"]

		# Orientation
		roll_rad, pitch_rad, yaw_rad = imu_euler_rad["roll"],imu_euler_rad["pitch"],imu_euler_rad["yaw"],
		roll_rad, pitch_rad, yaw_rad = -wrap_pi(roll_rad-math.pi), pitch_rad, -yaw_rad
		#print(f"roll={math.degrees(roll_rad)}pitch={pitch_rad}yaw={math.degrees(yaw_rad)}")

		# Magnetometer
		# mag_raw = magnetometer.get_mag_raw()
		# mag_x,mag_y,mag_z = mag_raw["mag_x"], mag_raw["mag_y"], mag_raw["mag_z"]
		# # magnetometer calibration
		# mx = mag_x - 25.5
		# my = mag_y - (-6.1)
		# mx_cal = mx / 132.05 * 129.825
		# my_cal = my / 127.6 * 129.825
		# yaw_mag = math.atan2(my_cal,-mx_cal)
		# #print("heading = ",heading)

		# mq_x, mq_y, mq_z, mq_w = euler_to_quaternion(roll_rad, pitch_rad, yaw_mag)

		# Serial Packet
		packet = {
			"timestamp":	elapsed_time,
			"odom_x":	position_x,
			"odom_y":	position_y,
			"odom_theta":	heading,
			"odom_linear_velocity": lin_v_vel,
			"odom_angular_velocity": ang_v_vel,
			"imu_accel_x": accel_x,
			"imu_accel_y": accel_y,
			"imu_accel_z": accel_z,
			"gyro_x": roll_rate,
			"gyro_y": pitch_rate,
			"gyro_z": yaw_rate,
			"imu_yaw": math.degrees(yaw_rad),
			"imu_roll": math.degrees(roll_rad),
			"imu_pitch":math.degrees(pitch_rad),
			# "qx":	mq_x,
			# "qy":	mq_y,
			# "qz":	mq_z,
			# "qw":	mq_w,
			# "mag_x": mag_x,
			# "mag_y": mag_y,
			# "mag_z": mag_z,
			"qx":	0.0,
			"qy":	0.0,
			"qz":	0.0,
			"qw":	0.0,
			"mag_x": 0.0,
			"mag_y": 0.0,
			"mag_z": 0.0,
		}

		message = json.dumps(packet).encode("utf-8")
		sock.sendto(message, (PC_IP, PC_PORT))

		# teleop cmd
		linear_cmd, angular_cmd = teleop.get_cmd()
		if teleop.timeout():
			linear_cmd = 0.0
			angular_cmd = 0.0

		left_wheel_cmd, right_wheel_cmd = rover.vel_cmd(linear_cmd,angular_cmd)
		left_wheel_cmd, right_wheel_cmd = math.degrees(left_wheel_cmd), math.degrees(right_wheel_cmd)
		left_wheel_cmd, right_wheel_cmd = converter.deg2mot(left_wheel_cmd), converter.deg2mot(right_wheel_cmd)
		#print(f"linx={linear_cmd}, angz={angular_cmd}")
		#print(f"lw={left_wheel_cmd},rw={right_wheel_cmd}")
		vel_cmd = {
			1: -left_wheel_cmd,
			2: right_wheel_cmd,
		}
		await vrishab.command(vel_cmd)
		await asyncio.sleep(0.01)

if __name__ == '__main__':
	# Initialization
	vrishab = MoteusInterface(servo_bus_map={1:[1],2:[2]},can_ids=[1,2])
	converter = GearReductionDeg(6)
	rover = DifferentialDrive(
		0.07305,      # Wheel radius [m]
		0.291,        # Distance between left and right wheels (wheel separation) [m]
		1.0,          # Gear ratio / scaling factor
		1.5708,       # Parameter value = pi/2 rad
		3 * math.pi,  # Parameter value = 3*pi rad
	)
	# magnetometer = MagnetometerRaw()

	# Serial Com
	PC_IP = "192.168.10.1"
	PC_PORT = 5000
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


	# Teleop receiver
	teleop = TeleopSubscriber(port=5006)


	try:
		# asyncio.run(main(vrishab,converter,rover,sock,magnetometer,teleop))
		asyncio.run(main(vrishab,converter,rover,sock,teleop))
	except KeyboardInterrupt:
		print("Disarming")

	finally:
		asyncio.run(vrishab.disarm())
