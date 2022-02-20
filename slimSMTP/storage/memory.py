import pydantic

class Memory(pydantic.BaseModel):
	transaction_serial_id :int = 0

	def begin_transaction(self, address):
		self.transaction_serial_id += 1
		return self.transaction_serial_id - 1

	def store_email(self, client):
		return True