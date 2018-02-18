import smtplib
import imp, importlib.machinery, signal, re
from ssl import wrap_socket, CERT_NONE
from socket import *
from select import epoll, EPOLLIN, EPOLLOUT, EPOLLHUP
from base64 import b64encode, b64decode
from time import sleep, strftime, localtime, time
from os import remove, getpid, kill, chown
from json import loads, dumps

from helpers import postgres, generate_UID, dCheck, log as logger, safeDict, signal_handler
from configuration import config as local_conf
from authentication import internal, pam

__builtins__.__dict__['log'] = logger
__builtins__.__dict__['config'] = local_conf

__date__ = '2018-02-18 22:23 CET'
__version__ = '0.1.0'
__author__ = 'Anton Hvornum'

runtimemap = {'_poller' : epoll(),
			  '_sockets' : {},
			  '_supports' : ['SIZE 10240000', 'STARTTLS', 'AUTH PLAIN LOGIN', 'ENHANCEDSTATUSCODES', '8BITMIME', 'DSN'],
			  '_login_methods' : {'_pam' : pam(), 'postgresql' : None, 'internal' : internal()},
			  '_clients' : {}
		   }

__builtins__.__dict__['runtime'] = runtimemap

def drop_privileges():
	return True

class client():
	def __init__(self, socket, addr, buffert=8192, data_pos=0, data=b'', username=None):
		self.socket = socket
		self.addr = addr
		self.buffer = buffert
		self.data = data
		self.data_pos = data_pos

		self.sslified = False
		self.username = username

	def send(self, bdata, lending=b'\r\n'):
		if not type(bdata) == bytes:
			bdata = bytes(bdata, 'UTF-8')

		self.socket.send(bdata+lending)

	def non_ssl_command(self, command):
		if command.lower() in ['ehlo', 'starttls']:
			return True
		return False

	def recv(self, buffert=None):
		if not buffert: buffert=self.buffer
		if self.sslified:
			data = self.socket.read(buffert)
		else:
			data = self.socket.recv(buffert)

		if len(data) <= 0:
			self.socket.close()
			return False
		self.data += data

		return True

	def parse(self):
		pass

#		if not self.sslified:
#			if self.data[self.data_pos:self.data_pos+4].lower() != 'ehlo' and self.data[self.data_pos:] != 'STARTTLS':
#				pass #print(self.data)

def terminate_socket(socket):
	runtime['_poller'].unregister(socket.fileno())
	del(runtime['_clients'][socket.fileno()])
	socket.close()
	return False

class mail_delivery(client):
	def __init__(self, socket, addr, *args, **kwargs):
		client.__init__(self, socket, addr, *args, **kwargs)

		self.email_catcher = re.compile(r'[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}')
		self.sender = None
		self.recievers = []
		self.data_parsing = False
		self.message = b''

	def domain(self, email):
		if type(email) == str: email = bytes(email, 'UTF-8')

		return email.split(b'@', 1)[1]

	def deliver(self):
		for reciever in self.recievers:
			if type(reciever) == bytes: reciever = reciever.decode('UTF-8')
			if not self.username and self.domain(reciever).decode('UTF-8') not in config['DOMAINS']:
				self.send('504 need to authenticate first')
				return terminate_socket(self.socket)

			if not reciever in config['mailboxes']:
				default_reciever = b'*@'+self.domain(reciever)
				if default_reciever.decode('UTF-8') in config['mailboxes']:
					log('Mailbox {} is not configured, but can default to {}'.format(reciever, default_reciever.decode('UTF-8')), host=self.addr, product='slimSMTP', handler='mail_delivery', level=3)
					reciever = default_reciever.decode('UTF-8')
				else:
					log('Mailbox {} is not configured.'.format(reciever), host=self.addr, product='slimSMTP', handler='mail_delivery', level=3)
					self.send('550 Address not configured on this site.')
					continue
			
			owner = config['mailboxes'][reciever]
			if type(owner) == bytes: owner = owner.decode('UTF-8')

			if not owner in config['users']:
				log('Owner {} of mailbox {} is not configured.'.format(owner, reciever), host=self.addr, product='slimSMTP', handler='mail_delivery', level=3)
				self.send('550 Address not configured on this site.')
				continue
			
			storage = config['users'][owner]['storage']
			storage.store(self.sender, reciever, self.message)
				
		self.send('250 2.0.0 Ok: queued as ' + b64encode(bytes(str(time()), 'UTF-8')).decode('utf-8'))
		return True

	def parse(self):
		if len(self.data):
			if not b'\r\n' in self.data[self.data_pos:]:
				return False

			if self.data_parsing:
				msgdata = self.data[self.data_pos:]
				self.data_pos += len(msgdata)
				self.message += msgdata

				if b'\r\n.\r\n' in self.message:
					self.message = self.message[0:self.message.rfind(b'\r\n.\r\n')]
					self.data_parsing = False

					log('Constructed mail from {} to {} with a message length of {}.'.format(self.sender, self.recievers, len(self.message)), host=self.addr, product='slimSMTP', handler='mail_delivery', level=3)
					return self.deliver()
			elif self.data_parsing is False and len(self.message) > 0:
				next_pos = self.data_pos
				for line in self.data[self.data_pos:].split(b'\r\n'):
					if len(line) <= 0:
						next_pos += 2
						continue

					if b'quit' == line.lower()[:len('quit')]:
						self.send('221 2.0.0 Bye')
						return terminate_socket(self.socket)

					next_pos += len(line)
				self.data_pos = next_pos
			else:
				next_pos = self.data_pos
				for line in self.data[self.data_pos:].split(b'\r\n'):
					if len(line) <= 0:
						next_pos += 2
						continue

					if b'mail from:' == line[:len('mail from:')].lower():
						senders = self.email_catcher.findall(line.decode('UTF-8'))
						if len(senders) == 1:
							self.sender = bytes(senders[0], 'UTF-8')
							domain = self.domain(self.sender).decode('UTF-8')

							if domain in config['DOMAINS'] and not self.username:
								log('User tried to send a protected e-mail sender without authentication.', host=self.addr, product='slimSMTP', handler='mail_delivery', level=10)
								self.send('504 need to authenticate first')
								return terminate_socket(self.socket)

							self.send('250 2.1.0 Ok')
						else:
							log('Invalid ammount of senders:', senders, host=self.addr, product='slimSMTP', handler='mail_delivery', level=10)
							return terminate_socket(self.socket)

					elif b'rcpt to:' == line.lower()[:len('rcpt to:')]:
						recievers = self.email_catcher.findall(line.decode('UTF-8'))

						if len(recievers):
							self.recievers = [bytes(x, 'UTF-8') for x in recievers]

							for reciever in self.recievers:
								domain = self.domain(reciever).decode('UTF-8')
								if domain not in config['DOMAINS'] and not self.username:
									log('{} domain is not in domains and requires auth'.format(domain), host=self.addr, product='slimSMTP', handler='mail_delivery', level=10)
									self.send('504 need to authenticate first')
									return terminate_socket(self.socket)

							self.send('250 2.1.5 Ok')

					elif b'data' == line.lower()[:len('data')]:
						self.data_parsing = True
						self.send('354 End data with <CR><LF>.<CR><LF>')

					next_pos += len(line)
				self.data_pos = next_pos

class auth_login(client):
	def __init__(self, socket, addr, *args, **kwargs):
		client.__init__(self, socket, addr, *args, **kwargs)
		self.send(b'334 ' + b64encode(b'Username:'))
		self.username = None
		self.password = None

	def parse(self):
		if len(self.data):
			if not b'\r\n' in self.data[self.data_pos:]:
				return False

			next_pos = self.data_pos
			for line in self.data[self.data_pos:].split(b'\r\n'):
				if len(line) <= 0:
					next_pos += 2
					continue
				if b'auth login' in line.lower()[:50]:
					next_pos += len(line)
					continue

				if self.username is None:
					self.username = b64decode(line)
					self.send(b'334 ' + b64encode(b'Password:'))

				elif self.password is None:
					self.password = b64decode(line)

				next_pos += len(line)
			self.data_pos = next_pos

		if self.username and self.password:
			for method in runtime['_login_methods']:
				if not runtime['_login_methods'][method]: continue # Disabled method

				if runtime['_login_methods'][method].authenticate(self.username, self.password):
					self.send(b'235 Authentication succeeded')
					runtime['_clients'][self.socket.fileno()] = mail_delivery(self.socket, self.addr, username=self.username, data=self.data, data_pos=self.data_pos+len(line+b'\r\n'))
					return True

			self.send('535 5.7.8 Error: authentication failed.')
			return self.terminate_socket(self.socket)

class auth_plain(client):
	def __init__(self, socket, addr, *args, **kwargs):
		client.__init__(self, socket, addr, *args, **kwargs)

	def parse(self):
		if len(self.data):
			if not b'\r\n' in self.data[self.data_pos:]:
				return False

			next_pos = self.data_pos
			for line in self.data[self.data_pos:].split(b'\r\n'):
				if len(line) <= 0:
					next_pos += 2
					continue

				if b'auth plain' in line.lower()[:30]:
					trash, trash, userdata = line.split(b' ', 2)
					trash, username, password = b64decode(userdata).split(b'\x00', 2)

					for method in runtime['_login_methods']:
						if not runtime['_login_methods'][method]: continue # Disabled method

						if runtime['_login_methods'][method].authenticate(username, password):
							self.send(b'235 Authentication succeeded')
							runtime['_clients'][self.socket.fileno()] = mail_delivery(self.socket, self.addr, username=username, data=self.data, data_pos=self.data_pos+len(line+b'\r\n'))
							return True

					self.send('535 5.7.8 Error: authentication failed.')
					return self.terminate_socket(self.socket)

				next_pos += len(line)
			self.data_pos = next_pos

runtime['_auth_methods'] = {b'login' : auth_login, b'plain' : auth_plain}

class pre_auth(client):
	def __init__(self, socket, addr):
		client.__init__(self, socket, addr)

	def parse(self):
		if len(self.data):
			if not b'\r\n' in self.data[self.data_pos:]:
				return False

			# 530 5.7.0 Must issue a STARTTLS command first

			next_pos = self.data_pos
			for line in self.data[self.data_pos:].split(b'\r\n'):
				if len(line) <= 0:
					next_pos += 2
					continue

				if b'ehlo' == line[:len('ehlo')].lower():
					log('{} said EHLO to us!'.format(self.addr), host=self.addr, product='slimSMTP', handler='pre_auth', level=1)
					for support in runtime['_supports'][:-1]:
						self.send('250-{}'.format(support))
					self.send('250 {}'.format(runtime['_supports'][-1]))

				elif b'starttls' == line[:len('starttls')].lower():
					log('Converted communication with {} to SSL.'.format(self.addr), host=self.addr, product='slimSMTP', handler='pre_auth', level=1)
					self.send('220 2.0.0 Ready to start TLS')
					self.socket = wrap_socket(self.socket, keyfile=config['ssl']['key'], certfile=config['ssl']['cert'], server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False, cert_reqs=CERT_NONE, ca_certs=None, ssl_version=config['ssl']['VERSION'])
					self.sslified = True

				elif b'auth' == line[:len('auth')].lower():
					tmp = line[5:1024].lower()
					tmp = tmp.split(b' ')
					method = tmp[0]
					log('{} wants to authenticate with {}.'.format(self.addr, method), host=self.addr, product='slimSMTP', handler='pre_auth', level=1)
					if method in runtime['_auth_methods']:
						runtime['_clients'][self.socket.fileno()] = runtime['_auth_methods'][method](self.socket, self.addr, data=self.data, data_pos=self.data_pos)
						break
					else:
						self.send('504 Authentication mechanism not supported.')
						return terminate_socket(self.socket)

				elif b'mail from' == line[:len('mail from')].lower():
					runtime['_clients'][self.socket.fileno()] = mail_delivery(self.socket, self.addr, data=self.data, data_pos=self.data_pos)

				next_pos += len(line)
			self.data_pos = next_pos

runtime['_sockets']['port_25'] = socket()
runtime['_sockets']['port_25'].setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
runtime['_sockets']['port_25'].bind(('', 25)) # TODO: 25
runtime['_sockets']['port_25'].listen(4)
runtime['_sockets']['port_587'] = socket()
runtime['_sockets']['port_587'].setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
runtime['_sockets']['port_587'].bind(('', 587))
runtime['_sockets']['port_587'].listen(4)
runtime['_sockets']['port_587'] = wrap_socket(runtime['_sockets']['port_587'], keyfile=config['ssl']['key'], certfile=config['ssl']['cert'], server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False, cert_reqs=CERT_NONE, ca_certs=None, ssl_version=config['ssl']['VERSION'])

runtime['_poller'].register(runtime['_sockets']['port_25'].fileno(), EPOLLIN)
runtime['_poller'].register(runtime['_sockets']['port_587'].fileno(), EPOLLIN)

while drop_privileges() is None:
	log('Waiting for privileges to drop.', product='slimSMTP', handler='smtp_main', once=True, level=5)

while 1:
	for fileno, eventid in runtime['_poller'].poll(config['poll_timeout']):
		if fileno == runtime['_sockets']['port_25'].fileno():
			ns, na = runtime['_sockets']['port_25'].accept()
			runtime['_poller'].register(ns.fileno(), EPOLLIN)
			
			log('Welcoming client {}'.format(na), host=na, product='slimSMTP', handler='main_loop', level=2)
			runtime['_clients'][ns.fileno()] = pre_auth(ns, na)
			runtime['_clients'][ns.fileno()].send(b'220 multi-domain.gw ESMTP SlimSMTP')
			
		if fileno == runtime['_sockets']['port_587'].fileno():
			ns, na = runtime['_sockets']['port_587'].accept()
			runtime['_poller'].register(ns.fileno(), EPOLLIN)

			log('Welcoming SSL client {}'.format(na), host=na, product='slimSMTP', handler='main_loop', level=2)
			runtime['_clients'][ns.fileno()] = pre_auth(ns, na)
			runtime['_clients'][ns.fileno()].send(b'220 multi-domain.gw ESMTP SlimSMTP')

		elif fileno in runtime['_clients']:
			if not runtime['_clients'][fileno].recv():
				runtime['_poller'].unregister(fileno)
				del(runtime['_clients'][fileno])

	#try:
	for fileno in list(runtime['_clients'].keys()):
		if fileno in runtime['_clients']:
			runtime['_clients'][fileno].parse()
	#except RuntimeError:
	#	Dictionary changed size during iteration

#runtime['_sockets']['port_587'].close()
runtime['_sockets']['port_25'].close()