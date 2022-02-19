import pydantic
from typing import List, Any

class Parser(pydantic.BaseModel):
	expectations: List[Any]

	def parse(self, cmd_data):
		for cmd_handler in self.expectations:
			if cmd_handler.can_hanadle(cmd_data):
				for result in cmd_handler.handle(cmd_data):
					yield result