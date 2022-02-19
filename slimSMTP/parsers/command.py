import pydantic
from typing import Callable, List
from ..realms import Realm
from ..sockets import Client
from ..exceptions import AuthenticationError

class CMD_DATA(pydantic.BaseModel):
	data: str
	realms: List[Realm]
	session: Client

class authenticated:
	def __init__(self, func, **kwargs):
		if type(func).__name__ == 'type':
			self.func = func

			return None

		if func.obj.session.authenticated == False:
			raise AuthenticationError(f"Session({func.session}) is not authenticated and can not perform CMD({func})")

	def can_hanadle(self, obj :CMD_DATA):
		return self.func.can_hanadle(obj)

	def handle(self, obj :CMD_DATA):
		for result in self.func.respond(obj):
			yield result

@authenticated
class EHLO:
	def can_hanadle(obj :CMD_DATA):
		return obj.data.lower().startswith('ehlo')

	def respond(obj :CMD_DATA):
		supports = [
			obj.realms[0].fqdn,
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

class QUIT:
	def can_hanadle(obj :CMD_DATA):
		return obj.data.lower().startswith('quit')

	def respond(obj :CMD_DATA):
		yield b'221 OK\r\n'

	def handle(obj :CMD_DATA):
		for result in QUIT.respond(obj):
			yield result

		obj.session.close()