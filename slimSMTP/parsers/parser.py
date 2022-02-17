import pydantic
from typing import List, Union
from .command import EHLO, QUIT

class Parser(pydantic.BaseModel):
	expectations: List[Union[EHLO, QUIT]]

	def parse(self, cmd_data):
		for cmd_handler in self.expectations:
			if cmd_handler.can_hanadle(cmd_data):
				for result in cmd_handler.handle(cmd_data):
					yield result