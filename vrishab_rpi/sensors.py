import serial
import asyncio

class MagnetometerRaw:
	def __init__(self):
		self.ser = serial.Serial('/dev/ttyUSB0', 115200)

		self.mag_raw = {
			"mag_x": 0,
			"mag_y": 0,
			"mag_z": 0,
		}

	async def read_mag(self):
		while True:
			try:
				line = self.ser.readline().decode().strip()
				x, y, z = map(float, line.split(','))

				self.mag_raw["mag_x"] = x
				self.mag_raw["mag_y"] = y
				self.mag_raw["mag_z"] = z
			except:
				pass
			await asyncio.sleep(0.1)

	def get_mag_raw(self):
		return self.mag_raw

'''
async def main():
	a = MagnetometerRaw()
	asyncio.create_task(a.read_mag())
	while True:
		b = a.get_mag_raw()
		print("b",b)
		await asyncio.sleep(0.005)

if __name__ == '__main__':
	asyncio.run(main())
'''
