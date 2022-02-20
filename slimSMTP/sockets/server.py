import socket
import time
import logging
from .sockets import epoll, EPOLLIN, EPOLLHUP
from ..configuration import Configuration
from ..logger import log

class Server:
	def __init__(self, configuration :Configuration):
		self.configuration = configuration
		self.socket = socket.socket()
		self.epoll = epoll()
		self.epoll.register(self.socket.fileno(), EPOLLIN | EPOLLHUP)
		self.clients = {}
		self.so_timeout = 0.025

		self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.socket.bind((self.configuration.address, self.configuration.port))
		self.socket.listen(4)

	def close(self):
		for client_fileno, client in self.clients.items():
			client.close()

		self.epoll.unregister(self.socket.fileno())
		self.socket.close()

	def process_idle_connections(self):
		time_check = time.time()
		for client_fileno, client in self.clients.items():
			if client.get_last_recieve() is None or time_check - client.get_last_recieve() > self.configuration.hanging_timeouts:
				log(f"Client({client}) was idle too long: {time_check - client.get_last_recieve()}", level=logging.DEBUG, fg="yellow")
				client.close()

				yield client

	def poll(self, timeout = None):
		from .clients import Client
		from ..mail.spam import is_spammer

		if not timeout:
			timeout = self.so_timeout

		for fileno, event_id in self.epoll.poll(timeout):
			if fileno != self.socket.fileno():
				continue

			client_socket, client_addr = self.socket.accept()

			if is_spammer(client_addr[0]):
				client_socket.close()
				continue

			self.clients[client_socket.fileno()] = Client(
				parent = self,
				socket = client_socket,
				address = client_addr
			)

			self.epoll.register(client_socket.fileno(), EPOLLIN | EPOLLHUP)

		return True

	def __iter__(self):
		filter_filenumbers = []
		for fileno, event_id in self.epoll.poll(self.so_timeout):
			if fileno == self.socket.fileno():
				continue

			filter_filenumbers.append(fileno)
			yield self.clients[fileno]

		for fileno in self.clients:
			if fileno in filter_filenumbers:
				continue

			if not len(self.clients[fileno].get_slice(0, 1)) == 1:
				continue

			yield self.clients[fileno]