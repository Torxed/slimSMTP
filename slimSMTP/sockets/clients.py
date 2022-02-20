import pydantic
import socket
import logging
import time
from typing import Tuple, Optional, TYPE_CHECKING
from .server import Server
from .sockets import EPOLLIN
from ..exceptions import InvalidSender
from ..logger import log

if TYPE_CHECKING:
	from ..parsers import Parser
	from ..parsers import CMD_DATA
	from ..mail import Mail

class Client(pydantic.BaseModel):
	parent :Server
	socket :socket.socket
	fileno :int
	address :Tuple[str, int]
	buffert :bytes = b''
	parser :Optional['Parser'] = None
	mail :'Mail' = None
	last_recieve :float = None
	authenticated :bool = False

	def __init__(self, **data):
		super().__init__(**data)

		try:
			data['socket'].send(bytes(f"220 {data['parent'].configuration.realms[0].fqdn} ESMTP\r\n", "UTF-8"))
		except (BrokenPipeError, ConnectionResetError):
			return self.close()

		if not self.last_recieve:
			self.last_recieve = time.time()

		from ..parsers import Parser, EHLO, QUIT
		self.parser = Parser(
			expectations=[
				EHLO,
				QUIT
			]
		)

	class Config:
		arbitrary_types_allowed = True

	def set_parser(self, parser :'Parser'):
		self.parent.clients[self.fileno].parser = parser

	def set_buffert(self, new_buffert :bytes):
		self.parent.clients[self.fileno].buffert = new_buffert

	def set_last_recieve(self, value):
		self.parent.clients[self.fileno].last_recieve = value

	def get_buffert(self):
		return self.parent.clients[self.fileno].buffert

	def get_slice(self, start, stop):
		return self.parent.clients[self.fileno].buffert[start:stop]

	def get_last_recieve(self):
		return self.parent.clients[self.fileno].last_recieve

	def close(self):
		try:
			self.parent.epoll.unregister(self.fileno)
		except (FileNotFoundError, OSError):
			# Not registered yet, so that's fine
			pass

		if self.fileno in self.parent.clients:
			del(self.parent.clients[self.fileno])

		self.socket.close()

		return None

	def get_data(self):
		from ..parsers import CMD_DATA

		if self.socket.fileno() == -1:
			return None

		if (self.fileno, EPOLLIN) in self.parent.epoll.poll(self.parent.so_timeout):
			try:
				new_data = self.socket.recv(8192)

				if len(new_data) == 0:
					return self.close()

				self.buffert += new_data
				self.set_last_recieve(time.time())
			except Exception as err:
				return self.close()

		if b'\r\n' in self.buffert:
			first_linebreak = self.get_buffert().find(b'\r\n')
			data = self.get_slice(0, first_linebreak)

			self.set_buffert(self.buffert[first_linebreak+2:])

			try:
				return CMD_DATA(
					data=data,
					realms=self.parent.configuration.realms,
					session=self
				)
			except pydantic.error_wrappers.ValidationError:
				self.close()


	def parse(self, data :'CMD_DATA'):
		try:
			for response in self.parser.parse(data):
				yield response
		except InvalidSender as error:
			from ..mail.spam import spammer

			self.close()
			spammer(self)
			log(f"Client({self}) is marked as a spammer: {error}", level=logging.WARNING, fg="red")


	def respond(self, data :bytes):
		self.socket.send(data)