import socket
from .sockets import epoll, EPOLLIN, EPOLLHUP
from ..configuration import Configuration

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

	def poll(self, timeout = None):
		from .clients import Client

		if not timeout:
			timeout = self.so_timeout

		for fileno, event_id in self.epoll.poll(timeout):
			if fileno != self.socket.fileno():
				continue

			client_socket, client_addr = self.socket.accept()

			self.clients[client_socket.fileno()] = Client(
				parent = self,
				socket = client_socket,
				address = client_addr
			)

			self.epoll.register(client_socket.fileno(), EPOLLIN | EPOLLHUP)

		return True

	def __iter__(self):
		for fileno, event_id in self.epoll.poll(self.so_timeout):
			if fileno == self.socket.fileno():
				continue

			yield self.clients[fileno]