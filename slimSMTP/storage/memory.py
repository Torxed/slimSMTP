from typing import TYPE_CHECKING
import pydantic

if TYPE_CHECKING:
	from ..sockets import Client

class Memory(pydantic.BaseModel):
	transaction_serial_id :int = 0

	def begin_transaction(self, address :str) -> int:
		self.transaction_serial_id += 1
		return self.transaction_serial_id - 1

	def store_email(self, client :Client) -> bool:
		return True

	def set_transaction_as_secure(self, transaction_id :int) -> None:
		return None