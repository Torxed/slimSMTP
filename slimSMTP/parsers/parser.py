import pydantic
from typing import List, Any, TYPE_CHECKING, Iterator

if TYPE_CHECKING:
	from .command import CMD_DATA

class Parser(pydantic.BaseModel):
	expectations: List[Any]

	def parse(self, cmd_data :CMD_DATA) -> Iterator[bytes]:
		for cmd_handler in self.expectations:
			if cmd_handler.can_hanadle(cmd_data):
				for result in cmd_handler.handle(cmd_data):
					yield result