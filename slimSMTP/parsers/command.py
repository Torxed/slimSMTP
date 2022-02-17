import pydantic
from typing import Callable
from ..realms import Realm

class CMD_DATA(pydantic.BaseModel):
	data: str
	realm: Realm

class Command(pydantic.BaseModel):
	string: str
	handler: Callable

	def can_hanadle(self, obj :CMD_DATA):
		return obj.data.lower().startswith(self.string)

	def handle(self, obj :CMD_DATA):
		for result in self.handler(obj).respond(obj):
			yield result

class EHLO(Command):
	def __init__(self, obj :CMD_DATA):
		super(EHLO, self).__init__(string='ehlo', handler=self)

	def respond(self, obj :CMD_DATA):
		supports = [
			obj.realm.fqdn,
			'PIPELINING',
			'SIZE 61440000',
			'STARTTLS',
			'ENHANCEDSTATUSCODES',
			'8BITMIME'
		]

		response = b''
		for index, support in enumerate(supports):
			if index != len(supports)-1:
				response += bytes(f"250-{support}\r\n", 'UTF-8')
			else:
				response += bytes(f"250 {support}\r\n", 'UTF-8')

		yield response

class QUIT(Command):
	def __init__(self, obj :CMD_DATA):
		super(EHLO, self).__init__(string='ehlo', handler=self)

	def respond(self, obj :CMD_DATA):
		pass