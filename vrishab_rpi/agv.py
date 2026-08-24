import math

class DifferentialDrive:
	def __init__(self,wheel_radius,wheel_base,max_linear_vel,max_angular_vel,max_wheel_vel):
		self.max_linear_vel = max_linear_vel
		self.max_angular_vel = max_angular_vel
		self.max_wheel_vel = max_wheel_vel
		self.wheel_radius = wheel_radius
		self.wheel_base = wheel_base
		self.pose = {
			"x": 0.0,
			"y": 0.0,
			"theta": 0.0,
		}
	def wheel_odometry(self,wheel_angular_velocity_left,wheel_angular_velocity_right,delta_t):

		self.linear_vel_left = self.wheel_radius*wheel_angular_velocity_left
		self.linear_vel_right = self.wheel_radius*wheel_angular_velocity_right

		self.linear_velocity = (self.linear_vel_right+self.linear_vel_left)/2
		self.angular_velocity = (self.linear_vel_right-self.linear_vel_left)/self.wheel_base

		x, y, theta = self.pose["x"], self.pose["y"], self.pose["theta"]

		x += self.linear_velocity * math.cos(theta)*delta_t
		y += self.linear_velocity * math.sin(theta)*delta_t
		theta += self.angular_velocity * delta_t
		lin_vel = self.linear_velocity
		ang_vel = self.angular_velocity

		self.pose["x"], self.pose["y"], self.pose["theta"] = x, y, theta
		return x,y,theta,lin_vel,ang_vel

	def vel_cmd(self,linear,angular):
		v = self.max_linear_vel * linear
		w = self.max_angular_vel * angular

		left_linear_vel = v - (self.wheel_base / 2.0) * w
		right_linear_vel = v + (self.wheel_base / 2.0) * w

		left_wheel_vel = left_linear_vel/self.wheel_radius
		right_wheel_vel = right_linear_vel/self.wheel_radius
		'''
		left_wheel_vel = max(
			-self.max_wheel_vel,
			min(self.max_wheel_vel,left_wheel_vel)
		)

		right_wheel_vel = max(
			-self.max_wheel_vel,
			min(self.max_wheel_vel,right_wheel_vel)
		)
		'''
		return left_wheel_vel,right_wheel_vel

class AngleUnwrapper:
	def __init__(self):
		self.prev = None
		self.unwrapped = 0.0

	def update(self, angle):
		if self.prev is None:
			self.prev = angle
			self.unwrapped = angle
			return self.unwrapped

		delta = angle - self.prev

		if delta > math.pi:
			delta -= 2* math.pi
		elif delta < -math.pi:
			delta += 2*math.pi

		self.unwrapped += delta
		self.prev = angle

		return self.unwrapped
