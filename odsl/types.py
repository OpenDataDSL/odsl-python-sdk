

class Curve:
	def __init__(self, ondate, expcal):
		self.contracts = []
		self.data = dict()
		self.data['_type'] = 'VarCurve'
		self.data['ondate'] = {
			'expiryCalendar': expcal,
			'curveDate': ondate
		}
		self.data['contracts'] = self.contracts

	def add(self, tenor, value):
		c = Contract(tenor, value)
		self.contracts.append(c.data)

class Contract:
	def __init__(self, tenor, value):
		self.data = dict()
		self.data['tenor'] = tenor
		self.data['value'] = value
