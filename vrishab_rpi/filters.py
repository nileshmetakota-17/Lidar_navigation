class LowPassFilter:
	def __init__(self,alpha):
		self.alpha = alpha
		self.y = None

	def update(self,x):
		if self.y is None:
			self.y = x
		else:
			self.y = self.alpha * x + (1-self.alpha) * self.y

		return self.y


