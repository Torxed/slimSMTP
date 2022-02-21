import pydantic
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from ..sockets import Client

class Memory(pydantic.BaseModel):
	transaction_serial_id :int = 0

	def begin_transaction(self, address :str) -> int:
		from ..logger import log
		log(f"Using dummy storage Memory()", level=logging.WARNING, fg="red")
		self.transaction_serial_id += 1
		return self.transaction_serial_id - 1

	def store_email(self, client :'Client') -> bool:
		from ..logger import log
		log(f"Using dummy storage Memory(), mail has not been stored", level=logging.WARNING, fg="red")
		return True

	def set_transaction_as_secure(self, transaction_id :int) -> None:
		from ..logger import log
		log(f"Using dummy storage Memory()", level=logging.WARNING, fg="red")
		return None