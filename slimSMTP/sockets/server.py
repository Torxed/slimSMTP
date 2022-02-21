import socket
import time
import logging
from typing import TYPE_CHECKING, Dict, Iterator, Optional
from .sockets import epoll, EPOLLIN, EPOLLHUP
from ..configuration import Configuration
from ..logger import log

if TYPE_CHECKING:
	from .clients import Client

class Server:
	def __init__(self, configuration :Configuration):
		self.configuration = configuration
		self.socket = socket.socket()
		self.epoll = epoll()
		self.epoll.register(self.socket.fileno(), EPOLLIN | EPOLLHUP)
		self.clients :Dict[int, Client] = {}
		self.so_timeout = 0.025

		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind((self.configuration.address, self.configuration.port))
		self.socket.listen(4)

	def close(self) -> None:
		for client_fileno, client in self.clients.items():
			client.close()

		self.epoll.unregister(self.socket.fileno())
		self.socket.close()

	def process_idle_connections(self) -> Iterator[Client]:
		time_of_check = time.time()
		# TODO: Might be more memory efficient to not convert .items() to list()
		# but that would mean we'd have to clean up any closed clients here after the loop
		for client_fileno, client in list(self.clients.items()):
			if (last_recieve := client.get_last_recieve()) and time_of_check - last_recieve > self.configuration.hanging_timeouts:
				log(f"Client({client}) was idle too long: {self.configuration.hanging_timeouts}", level=logging.DEBUG, fg="yellow")
				client.close()

				yield client
			elif last_recieve is None:
				log(f"Client({client}) was idle too long: {self.configuration.hanging_timeouts}", level=logging.DEBUG, fg="yellow")
				client.close()

				yield client

	def poll(self, timeout :Optional[float] = None) -> bool:
		from .clients import Client
		from ..mail.spam import is_spammer
		from ..parsers import Parser
		from ..mail import Mail

		if not timeout:
			timeout = self.so_timeout

		for fileno, event_id in self.epoll.poll(timeout):
			if fileno != self.socket.fileno():
				continue

			client_socket, client_addr = self.socket.accept()
			client_fileno = client_socket.fileno()

			if is_spammer(client_addr[0]):
				client_socket.close()
				continue

			Client.update_forward_refs(Parser=Parser, Mail=Mail)

			self.clients[client_fileno] = Client(
				parent=self,
				socket=client_socket,
				fileno=client_fileno,
				address=client_addr,
				mail=Mail(
					session=self,
					client_fd=client_fileno,
					transaction_id=self.configuration.storage.begin_transaction(client_addr)
				)
			)

			if client_socket.fileno() != -1:
				self.epoll.register(client_socket.fileno(), EPOLLIN | EPOLLHUP)

		return True

	def __iter__(self) -> Iterator[Client]:
		filter_filenumbers = []
		for fileno, event_id in self.epoll.poll(self.so_timeout):
			if fileno == self.socket.fileno():
				continue

			filter_filenumbers.append(fileno)
			yield self.clients[fileno]

		for fileno in list(self.clients.keys()):
			if fileno in filter_filenumbers:
				continue

			if not len(self.clients[fileno].get_slice(0, 1)) == 1:
				continue

			yield self.clients[fileno]