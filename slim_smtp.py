#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
import asyncore, re, smtplib, ssl
from base64 import b64encode, b64decode
from threading import *
from socket import *
from time import sleep, strftime, localtime, time
from os import _exit
from os.path import isfile

__date__ = '2013-07-07 14:50 CET'
__version__ = '0.0.1'

core = {'_socket' : {'listen' : '', 'port' : 25, 'SSL' : True},
		'SSL' : {'key' : '/storage/certificates/server.key', 'cert' : '/storage/certificates/server.crt', 'VERSION' : ssl.PROTOCOL_TLSv1|ssl.PROTOCOL_SSLv3},
		'domain' : 'example.se',
		'supports' : ['example.se', 'SIZE 10240000', 'STARTTLS', 'AUTH PLAIN', 'ENHANCEDSTATUSCODES', '8BITMIME', 'DSN'],
		'users' : {'test' : {'password' : 'passWord123'}},
		'relay' : ('smtp.t3.se', 25, False),
		'storages' : {'test@example.se' : '/storage/mail/test',
					'default' : '/storage/mail/unsorted'}}

def getDomainInfo(domain):
	if '@' in domain:
		domain = domain.split('@',1)[1]
	
	if domain.count('.') > 2:
		host, domain = domain.split('.',1)
	else:
		host = None

	return host, domain

def local_mail(_from, _to, message):
	if _to in core['storages']:
		path = core['storages'][_to] + '/'
	else:
		path = core['storages']['default'] + '/'

	with open(path + _from + '-' + str(time()) + '.mail', 'wb') as fh:
		fh.write(message)

	return True

def external_mail(_from, to, message):
	Fail = False
	server = smtplib.SMTP(core['relay'][0], core['relay'][1])
	server.ehlo()
	if core['relay'][2]:
		try:
			server.starttls()
		except:
			print ' ! The relay-server doesn\'t support TLS/SSL!'
			return False
	if len(core['relay']) >= 5:
		server.login(core['relay'][3], core['relay'][4])

	try:
		server.sendmail(_from, to, message)
	except smtplib.SMTPRecipientsRefused:
		print ' ! Could not relay the mail, Recipient Refused!'
		Fail = True
	except:
		Fail = True

	server.quit()

	return Fail

class _clienthandle(Thread):
	def __init__(self, sock, addr):
		self.socket = sock
		self.addr = addr
		self.disconnect = False

		self.session = None
		self._from = None
		self._to = None
		self.data = ''
		self.external = False
		self.ssl = False

		self.email_catcher = re.compile(r'[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}')

		Thread.__init__(self)
		self.start()

	def run(self):
		recieved_data = ''
		data_mode = False
		while self.disconnect == False:
			try:
				if self.ssl:
					data = self.socket.read()
				else:
					data = self.socket.recv(8192)
			except:
				data = None

			if not data:
				print ' - ' + str(self.addr[0]) + ' disconnected unexpectedly'
				break

			## To enforce SSL:
			# 530 5.7.0 Must issue a STARTTLS command first
			if core['_socket']['SSL'] and self.ssl == False and (data[:4] != 'EHLO' and data != 'STARTTLS'):
				if not 'STARTTLS' in data:
					self.socket.send('530 5.7.0 Must issue a STARTTLS command first\r\n')
					break
				else:
					self.socket.send('220 2.0.0 Ready to start TLS\r\n')
					self.socket = ssl.wrap_socket(self.socket, keyfile=core['SSL']['key'], certfile=core['SSL']['cert'], server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False, cert_reqs=ssl.CERT_NONE, ca_certs=None, ssl_version=core['SSL']['VERSION'])
					self.ssl = True
					print ' | Converted into a SSL socket!'
					continue

			response = ''
			recieved_data += data

			if data_mode and self.session:
				if not '\r\n.\r\n' in recieved_data: continue
				self.data, recieved_data = recieved_data.rsplit('\r\n.\r\n',1)
				data_mode = False
				print ' | Sending mail:'
				print ' - ' + self._from + '(' + self.session + ') -> ' + self._to
				if self.external:
					if external_mail(self._from, self._to, self.data + '\r\n.\r\n'):
						response += '250 2.0.0 Ok: queued as C8C7E2ED4D9C\r\n'
					else:
						response += '550 Could not deliver the e-mail externally (rejected)\r\n'
				else:
					local_mail(self._from, self._to, self.data)
					response += '250 2.0.0 Ok: queued as C8C7E2ED4D9C\r\n'

			while '\r\n' in recieved_data:
				command_to_parse, recieved_data = recieved_data.split('\r\n',1)
				print '<<',[command_to_parse]

				if command_to_parse[:4] == 'EHLO':
					for support in core['supports']:
						if core['supports'][-1] == support:
							response += '250 ' + support + '\r\n'
						else:
							response += '250-' + support + '\r\n'

				## TODO: Don't assume that the sender actually send a proper e-amil.
				## Also, this list might contain [] because of it.
				elif command_to_parse[:4] == 'MAIL':
					self._from = self.email_catcher.findall(command_to_parse)[0]
					response += '250 2.1.0 Ok\r\n'

				elif command_to_parse[:4] == 'RCPT':
					self._to = self.email_catcher.findall(command_to_parse)[0]
					if getDomainInfo(self._to)[1] != core['domain']:
						if not self.session:
							response += '504 need to authenticate first\r\n'
							break
						else:
							self.external = True
					else:
						if not self.session:
							self.session = '#incomming_externally'
					response += '250 2.1.5 Ok\r\n'

				elif command_to_parse == 'QUIT':
					response += '221 2.0.0 Bye\r\n'
					self.disconnect = True
					break

				elif command_to_parse[:4] == 'DATA' and self.session:
						data_mode = True
						response += '354 End data with <CR><LF>.<CR><LF>\r\n'

				elif not self.session and command_to_parse[:4] == 'AUTH':
					trash, mode = command_to_parse.split(' ',1)
					if mode[:5] == 'PLAIN':
						mode, password = mode.split(' ',1)
						authid, username, password = b64decode(password).split('\x00',2)
						if username in core['users'] and core['users'][username]['password'] == password:
							self.session = username
							response += '235 2.7.0 Authentication successful\r\n'
						else:
							print ' ! No such user:',[username]
							# 535 5.7.1 authentication failed\r\n
							response += '535 5.7.8 Error: authentication failed\r\n'
						break
						del password
					elif mode[:5] == 'LOGIN':
						response += '504 Authentication mechanism not supported.\r\n'
						# response += '335 ' + b64encode('Username:') + '\r\n'
						# <- b64decode(username)
						# response += '335 ' + b64encode('Password:') + '\r\n'
						# <- b64decode(password)
						# ...
				else:
					response += '504 need to authenticate first\r\n'
					break

			if len(response) > 0:
				print '>>',[response]
				self.socket.send(response)
				
		try:
			self.socket.close()
		except:
			pass

class _socket(Thread, socket):
	def __init__(self):
		socket.__init__(self)

		while 1:
			try:
				self.bind((core['_socket']['listen'], core['_socket']['port']))
				break
			except:
				sleep(5)
		self.listen(4)

		print ' | Bound to ' + ':'.join((core['_socket']['listen'], str(core['_socket']['port'])))

		Thread.__init__(self)
		self.start()

	def run(self):
		while 1:
			ns, na = self.accept()

			if not 'clients' in core:
				core['clients'] = {}

			core['clients'][str(na[0]) + ':' + str(na[1])] = {'socket' : ns, 'address' : na}

			ns.send('220 ' + core['domain'] + ' ESMTP SlimSMTP\r\n')
			ch = _clienthandle(ns, na)

s = _socket()
while 1:
	try:
		sleep(1)
	except:
		break

#for client in core['clients']:
#	try:
#		core['clients'][client]['socket'].close()
#	except:
#		pass
#s.close()
#_exit(1)