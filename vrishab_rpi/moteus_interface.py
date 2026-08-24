import asyncio
import math
import time

import moteus
import moteus_pi3hat

class MoteusInterface:
	def __init__(self,servo_bus_map,can_ids):
		self.servo_bus_map = servo_bus_map
		self.can_ids = can_ids
		self.transport = moteus_pi3hat.Pi3HatRouter(servo_bus_map=self.servo_bus_map)
		self.servos = {
			servo_id : moteus.Controller(id=servo_id,transport=self.transport)
			for servo_id in can_ids
		}
		self.results = None
		self.motor_position = {
			1: 0,
			2: 0,
		}
		self.motor_velocity = {
			1: 0,
			2: 0,
		}
		self.imu_angular_rate = {
			"roll_rate": 0,
			"pitch_rate": 0,
			"yaw_rate": 0,
		}

		self.imu_euler_rad = {
			"roll": 0,
			"pitch": 0,
			"yaw" : 0,
		}

		self.imu_quaternion = {
			"w": 0,
			"x": 0,
			"y": 0,
			"z": 0,
		}

		self.imu_accel_mps2 = {
			"x": 0,
			"y": 0,
			"z": 0,
		}

	async def disarm(self):
		print("Disarming Motors...")
		await self.transport.cycle([x.make_stop() for x in self.servos.values()])

	async def calibrate(self):
		print("Calibrating Motors...")
		await self.transport.cycle([x.make_set_output_exact(position=0.0) for x in self.servos.values()])
		print("Do not move the motors...")
		await asyncio.sleep(2)
		print("Motors Calibrated")

	async def read_motor_states(self):
		while True:
			states = await self.transport.cycle([x.make_query() for x in self.servos.values()])
			for state in states:
				self.motor_position[state.id] = state.values[moteus.Register.POSITION]
				self.motor_velocity[state.id] = state.values[moteus.Register.VELOCITY]
			await asyncio.sleep(0.005)

	def get_states(self):
		return{
			"left_pos":	self.motor_position[1],
			"right_pos":	self.motor_position[2],
			"left_vel":	self.motor_velocity[1],
			"right_vel":	self.motor_velocity[2],
		}

	async def command(self,velocity_map):
		commands = [
			self.servos[servo_id].make_position(
				position = math.nan,
				velocity = velocity_map[servo_id],
				velocity_limit = 10.0,
				accel_limit = 6.5,
				query = False,
			)
			for servo_id in self.can_ids
		]
		self.results = await self.transport.cycle(commands)

	async def imu(self):
		while True:
			imu_result = await self.transport.attitude()

			self.imu_angular_rate["roll_rate"] = math.radians(imu_result.rate_dps.x)
			self.imu_angular_rate["pitch_rate"] = math.radians(imu_result.rate_dps.y)
			self.imu_angular_rate["yaw_rate"] = math.radians(imu_result.rate_dps.z)
			self.imu_euler_rad["roll"] = imu_result.euler_rad.roll
			self.imu_euler_rad["pitch"] = imu_result.euler_rad.pitch
			self.imu_euler_rad["yaw"] = imu_result.euler_rad.yaw
			self.imu_quaternion["w"] = imu_result.attitude.w
			self.imu_quaternion["x"] = imu_result.attitude.x
			self.imu_quaternion["y"] = imu_result.attitude.y
			self.imu_quaternion["z"] = imu_result.attitude.z
			self.imu_accel_mps2["x"] = imu_result.accel_mps2.x
			self.imu_accel_mps2["y"] = imu_result.accel_mps2.y
			self.imu_accel_mps2["z"] = imu_result.accel_mps2.z

			await asyncio.sleep(0.005)

	def get_imu(self):
		return self.imu_angular_rate,self.imu_euler_rad,self.imu_quaternion,self.imu_accel_mps2

class GearReductionDeg:
	def __init__(self,reduction):
		self.scale = reduction/360
		self.reduction = reduction
	def deg2mot(self, deg):
		return self.scale * deg
	def mot2deg(self, mpos):
		return mpos/self.scale
'''
async def main():
	now = time.time()
	vrishab = MoteusInterface(servo_bus_map={1:[1],2:[2]},can_ids=[1,2])
	await vrishab.disarm()
	vrishab.get_states()
	#await vrishab.calibrate()
	#vrishab.get_states()

	velocity_map = {
		1: 0.5,
		2: 0.5,
	}
	elapsed_time = 0
	while elapsed_time <= 4.0:
		current_time = time.time()
		elapsed_time = current_time - now
		print("elapsed_time = ",elapsed_time)
		await vrishab.command(velocity_map)
		vrishab.get_states()

	#await asyncio.sleep(2.5)
	await vrishab.disarm()

if __name__ == '__main__':
	asyncio.run(main())

'''
