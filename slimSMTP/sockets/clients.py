import pydantic
import socket
from typing import Tuple, Optional, TYPE_CHECKING
from .server import Server
from .sockets import EPOLLIN
if TYPE_CHECKING:
	from ..parsers import Parser
	from ..parsers import CMD_DATA

class Client(pydantic.BaseModel):
	parent :Server
	socket :socket.socket
	address :Tuple[str, int]
	buffert :bytes = b''
	parser :Optional['Parser'] = None

	def __init__(self, **data):
		data['socket'].send(bytes(f"220 {data['parent'].configuration.realms[0].fqdn} ESMTP\r\n", "UTF-8"))
		super().__init__(**data)

	class Config:
		arbitrary_types_allowed = True

	def close(self):
		self.parent.epoll.unregister(self.socket.fileno())
		self.socket.close()

	def get_data(self):
		from ..parsers import CMD_DATA

		if (self.socket.fileno(), EPOLLIN) in self.parent.epoll.poll(self.parent.so_timeout):
			self.buffert += self.socket.recv(8192)

		if b'\r\n' in self.buffert:
			first_linebreak = self.buffert.find(b'\r\n')
			data = self.buffert[:first_linebreak]
			self.buffert = self.buffert[first_linebreak+2:]

			return CMD_DATA(
				data=data,
				realms=self.parent.configuration.realms,
				session=self
			)

	def parse(self, data :'CMD_DATA'):
		from ..parsers import Parser, EHLO, QUIT

		if not self.parser:
			self.parser = Parser(
				expectations=[
					EHLO,
					QUIT
				]
			)

		for response in self.parser.parse(data):
			yield response

	def respond(self, data :bytes):
		self.socket.send(data)