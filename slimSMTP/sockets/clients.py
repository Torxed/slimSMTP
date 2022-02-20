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
	address :Tuple[str, int]
	buffert :bytes = b''
	parser :Optional['Parser'] = None
	mail: 'Mail' = None
	last_recieve: float = time.time()

	def __init__(self, **data):
		super().__init__(**data)

		try:
			data['socket'].send(bytes(f"220 {data['parent'].configuration.realms[0].fqdn} ESMTP\r\n", "UTF-8"))
		except BrokenPipeError:
			return self.close()


		from ..parsers import Parser, EHLO, QUIT
		from ..mail import Mail
		self.parser = Parser(
			expectations=[
				EHLO,
				QUIT
			]
		)
		self.mail = Mail(session=self.parent, client_fd=self.socket.fileno())

	class Config:
		arbitrary_types_allowed = True

	def set_parser(self, parser :'Parser'):
		if self.socket.fileno() != -1:
			self.parent.clients[self.socket.fileno()].parser = parser

	def set_buffert(self, new_buffert :bytes):
		if self.socket.fileno() != -1:
			self.parent.clients[self.socket.fileno()].buffert = new_buffert

	def get_buffert(self):
		if self.socket.fileno() != -1:
			return self.parent.clients[self.socket.fileno()].buffert
		return b''

	def get_slice(self, start, stop):
		if self.socket.fileno() != -1:
			return self.parent.clients[self.socket.fileno()].buffert[start:stop]
		return b''

	def get_last_recieve(self):
		if self.socket.fileno() != -1:
			return self.parent.clients[self.socket.fileno()].last_recieve

	def set_last_recieve(self, value):
		if self.socket.fileno() != -1:
			self.parent.clients[self.socket.fileno()].last_recieve = value

	def close(self):
		if self.socket.fileno() != -1:
			try:
				self.parent.epoll.unregister(self.socket.fileno())
			except FileNotFoundError:
				# Not registered yet, so that's fine
				pass
			self.socket.close()

		return None

	def get_data(self):
		from ..parsers import CMD_DATA

		if self.socket.fileno() == -1:
			return None

		if (self.socket.fileno(), EPOLLIN) in self.parent.epoll.poll(self.parent.so_timeout):
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

			return CMD_DATA(
				data=data,
				realms=self.parent.configuration.realms,
				session=self
			)


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