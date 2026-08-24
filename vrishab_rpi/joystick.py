import pygame

class Joystick:
	def  __init__(self):
		pygame.init()
		pygame.joystick.init()

		self.joy = pygame.joystick.Joystick(0)
		self.joy.init()

		self.axis = {}
		self.buttons = {}

		self.prev_buttons = {}

	def update(self):
		pygame.event.pump()

		# Read axes
		self.axis["left_x"] = self.joy.get_axis(0)
		self.axis["left_y"] = self.joy.get_axis(1)
		self.axis["right_x"] = self.joy.get_axis(3)
		self.axis["right_y"] = self.joy.get_axis(5)

		# Read buttons
		self.prev_buttons = self.buttons.copy()

		self.buttons["cross"] = self.joy.get_button(0)
		self.buttons["circle"] = self.joy.get_button(1)
		self.buttons["triangle"] = self.joy.get_button(2)
		self.buttons["square"] = self.joy.get_button(3)

	def apply_deadzone(self,value,deadzone=0.1):
		if abs(value) < deadzone:
			return 0.0
		sign = 1.0 if value > 0 else -1.0

		return sign * (abs(value) - deadzone) / (1.0 - deadzone)

	def pressed(self,name):
		return (
			self.buttons.get(name,0)
			and not self.prev_buttons.get(name, 0)
		)

	def released(self, name):
		return (
			not self.buttons.get(name, 0)
			and self.prev_buttons.get(name, 0)
		)

	def get_twist(self):
		linear = self.apply_deadzone(-self.axis["left_y"])
		angular = self.apply_deadzone(-self.axis["right_x"])

		return linear, angular
'''
def main():
	joystick = Joystick()

	while True:
		joystick.update()
		linear, angular = joystick.get_twist()

		#print("linear = ",linear)
		#print("angular = ", angular)

		if joystick.pressed("cross"):
			print("Cross pressed")

if __name__ == '__main__':
	main()
'''
