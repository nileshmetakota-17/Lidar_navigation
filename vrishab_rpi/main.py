import asyncio
import math
import time
import socket
import json

import moteus
import moteus_pi3hat
import pygame

from moteus_interface import MoteusInterface, GearReductionDeg
from agv import DifferentialDrive, AngleUnwrapper
from joystick import Joystick

async def main():
	# Initialization
	vrishab = MoteusInterface(servo_bus_map={1:[1],2:[2]},can_ids=[1,2])
	converter = GearReductionDeg(1)
	rover = DifferentialDrive(0.2667,0.3565,1.0,1.5708,3*3.14)
	prev_time = time.time()
	start_time = time.time()

	joystick = Joystick()

	# Serial com
	PC_IP = "192.168.10.1"
	PC_PORT = 5000

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	# reset driver faults
	await vrishab.disarm()

	# Joystick
	Throttle = 0	# Placeholder for joy throttle input
	Steer = 0	# Placeholder for joy steering input

	# Initializing wheel data
	asyncio.create_task(vrishab.read_motor_states())
	asyncio.create_task(vrishab.imu())
	while True:
		joystick.update()
		linear, angular = joystick.get_twist()
		#print("Linear = ",linear)

		current_time = time.time()
		elapsed_time = current_time - start_time
		delta_t = current_time-prev_time
		prev_time = current_time

		states = vrishab.get_states()
		left_pos = converter.mot2deg(states["left_pos"])
		right_pos = converter.mot2deg(states["right_pos"])
		left_vel = math.radians(converter.mot2deg(states["left_vel"]))
		right_vel = math.radians(converter.mot2deg(states["right_vel"]))

		# IMU
		imu_rate,imu_euler_rad = vrishab.get_imu()
		roll_rate,pitch_rate,yaw_rate = imu_rate["roll_rate"], imu_rate["pitch_rate"], imu_rate["yaw_rate"]
		roll, pitch, yaw = imu_euler_rad["roll"], imu_euler_rad["pitch"], imu_euler_rad["yaw"]
		#print("yaw", yaw)

		# Odometry
		pos_x,pos_y,heading_yaw = rover.wheel_odometry(left_vel,right_vel,yaw,delta_t)
		#print("odom = ",odom)

		# Cmd
		left_wheel_cmd, right_wheel_cmd = rover.vel_cmd(linear,angular)
		#print(f"left_wheel={left_wheel_cmd},right_wheel={right_wheel_cmd}")

		left_wheel_cmd, right_wheel_cmd = math.degrees(left_wheel_cmd), math.degrees(right_wheel_cmd)
		left_wheel_cmd, right_wheel_cmd = converter.deg2mot(left_wheel_cmd),converter.deg2mot(right_wheel_cmd)
		#print(f"left_wheel={left_wheel_cmd},right_wheel={right_wheel_cmd}")

		vel_cmd = {
			1: left_wheel_cmd,
			2: right_wheel_cmd,
		}

		await vrishab.command(vel_cmd)

		packet = {
			"elapsed_time":		elapsed_time,
			"left_wheel_velocity":	left_vel,
			"right_wheel_velocity":	right_vel,
			"position_x":		pos_x,
			"position_y":		pos_y,
			"heading":		heading_yaw,
		}

		message = json.dumps(packet).encode("utf-8")
		sock.sendto(message, (PC_IP, PC_PORT))

		await asyncio.sleep(0.005)

if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		print("disarming")
	finally:
		vrishab1 = MoteusInterface(servo_bus_map={1:[1],2:[2]},can_ids=[1,2])
		print("stopping")
		asyncio.run(vrishab1.disarm())
