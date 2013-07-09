#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
import asyncore, re, smtplib, ssl
from base64 import b64encode, b64decode
from threading import *
from socket import *
from time import sleep, strftime, localtime, time
from os import _exit
from os.path import isfile, isdir

__date__ = '2013-07-09 16:15 CET'
__version__ = '0.0.5p1'

core = {'_socket' : {'listen' : '', 'port' : 25, 'SSL' : True},
		'SSL' : {'key' : '/storage/certificates/server.key', 'cert' : '/storage/certificates/server.crt', 'VERSION' : ssl.PROTOCOL_TLSv1|ssl.PROTOCOL_SSLv3},
		'domain' : 'example.se',
		'supports' : ['example.se', 'SIZE 10240000', 'STARTTLS', 'AUTH PLAIN', 'ENHANCEDSTATUSCODES', '8BITMIME', 'DSN'],
		'users' : {'test' : {'password' : 'passWord123'}},
		'relay' : ('smtp.relay.se', 25, False),
		'storages' : {'test@example.se' : '/storage/mail/test',
					'default' : '/storage/mail/unsorted'}}

class SanityCheck(Exception):
	pass

def sanity_startup_check():
	if not isfile(core['SSL']['key']):
		raise SanityCheck('Certificate error: Missing Key')
	if not isfile(core['SSL']['cert']):
		raise SanityCheck('Certificate error: Missing Cert')
	for storages in core['storages']:
		if not isdir(core['storages'][storages]):
			print ' ! Warning - Missing storage: ' + core['storages'][storages]
			## TODO: Create these missing folders,
			##       but do it in a clean non-introusive way
			##       (for instance, having default storage to /var would cause issues)

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
	server = smtplib.SMTP(core['relay'][0], core['relay'][1])
	server.ehlo()
	if core['relay'][2]:
		try:
			server.starttls()
		except:
			print ' ! The relay-server doesn\'t support TLS/SSL!'
			server.quit()
			return False
	if len(core['relay']) >= 5:
		try:
			server.login(core['relay'][3], core['relay'][4])
		except:
			print ' ! Invalid credentials towards relay server'
			server.quit()
			return False
	try:
		server.sendmail(_from, to, message)
	except smtplib.SMTPRecipientsRefused:
		print ' ! Could not relay the mail, Recipient Refused!'
		server.quit()
		return False
	except:
		server.quit()
		return False

	server.quit()
	return True

class parser():
	def __init__(self):
		self.authed_session = None
		self.From = None
		self.to = None
		self.data = ''
		self.external = False
		self.ssl = False
		self.email_catcher = re.compile(r'[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}')

		self.data_mode = False

	def reset(self):
		self.authed_session = None
		self.From = None
		self.to = None
		self.data = ''
		self.external = False
		self.ssl = False

		## We don't reset the data_mode,
		## mainly because reset is called inside the data loop.

	def deliver(self):
		print ' | Sending mail: ' + self.From + '(' + self.authed_session + ') -> ' + self.to
		## == Just to make sure, as long as we're authenticated and the authenticated "user"
		## == doesn't begin with an "#" (reserved for system-design-users), we'll send externally.
		if self.external and self.authed_session and self.authed_session[0] != '#':
			if external_mail(self.From, self.to, self.data + '\r\n.\r\n'):
				self.reset()
				return '250 2.0.0 Ok: queued as ' + b64encode(str(time())) + '\r\n'
		elif self.external and not self.authed_session:
			return '504 need to authenticate first\r\n'
		elif not self.external:
			local_mail(self.From, self.to, self.data)
			self.reset()
			return '250 2.0.0 Ok: Delivered\r\n'
		
		return '550 Could not deliver the e-mail\r\n'

	def login(self, data):
		trash, mode = data.split(' ',1)
		if mode[:5] == 'PLAIN':
			mode, password = mode.split(' ',1)
			authid, username, password = b64decode(password).split('\x00',2)
			if username in core['users'] and core['users'][username]['password'] == password:
				self.authed_session = username
				response += '235 2.7.0 Authentication successful\r\n'
			else:
				print ' ! No such user:',[username]
				# 535 5.7.1 authentication failed\r\n
				response += '535 5.7.8 Error: authentication failed\r\n'
			del password
		elif mode[:5] == 'LOGIN':
			response += '504 Authentication mechanism not supported.\r\n'
			# response += '335 ' + b64encode('Username:') + '\r\n'
			# <- b64decode(username)
			# response += '335 ' + b64encode('Password:') + '\r\n'
			# <- b64decode(password)
			# ...
		else:
			params = None
			if ' ' in mode:
				mode, params = mode.split(' ',1)
			if isfile(mode+'.py'):
				handle = __import__(mode)
				self.authed_session, response_add = handle.login(params)
				response += response_add
			else:
				response += '504 Authentication mechanism not supported.\r\n'
			del params
		return response

	def parse(self, data):
		response = ''

		if self.data_mode and self.authed_session:
			if '\r\n.\r\n' in data:
				self.data, data = data.rsplit('\r\n.\r\n', 1)
				self.data_mode = False
				response += self.deliver()
			else:
				self.data += data

		## The parsed data might be partial data for an e-mail body,
		## Hence we need to check for data_mode again to ensure that we don't
		## accidently parse something inside the message body in case the client
		## sends the message body over in odd chunks (maliscious packaging),
		## for instance:
		##
		## from: ...
		## to: ...
		## subject: ...
		## hello ]
		## [QUIT]
		## [your stupid complaints]
		## [or]
		## [else...]
		## \r\n.\r\n
		##
		## This message sent with odd chunks would cause us to QUIT if we parsed
		## this message below hence we have to honor the data_mode, for now.
		if not self.data_mode:
			## Some (most) clients BULK commands meaning we need to parse them
			## in order of their arrival and respond to them accordingly.
			while '\r\n' in data:
				command_to_parse, data = data.split('\r\n',1)
				## Debug:
				#print '<<',[command_to_parse]

				## ==
				## == The following commands are to be considered
				## == safe to parse whenever, both authorized and unauthorized.
				## ==
				if command_to_parse[:4] == 'EHLO':
					## == Upon EHLO, we reply with "250 <support>\r\n" until
					## == The last MODE we support, the last MODE is replied with "250 "
					## == and doesnt include "-", as such:
					## ==     250-<domain<\r\n
					## ==     250-<mode>\r\n
					## ==     250-<mode>\r\n
					## ==     250 <last mode>\r\n
					## == so we have to treat that last supported mode a bit different.
					for index in range(0, len(core['supports'])-2):
							response += '250-' + core['supports'][index] + '\r\n'
					response += '250 ' + core['supports'][-1] + '\r\n'

				elif command_to_parse[:4] == 'MAIL':
					## TODO: Don't assume that the sender actually send a proper e-amil.
					## Also, this list might contain [] because of it.
					self.From = self.email_catcher.findall(command_to_parse)[0]
					response += '250 2.1.0 Ok\r\n'

				elif command_to_parse[:4] == 'RCPT':
					## TODO: Don't assume that the sender actually send a proper e-amil.
					## Also, this list might contain [] because of it.
					self.to = self.email_catcher.findall(command_to_parse)[0]
					if getDomainInfo(self.to)[1] != core['domain']:
						## If the sender is trying to relay anything except our own domain
						## we'll tell the user to authenticate first.
						if not self.authed_session:
							response += '504 need to authenticate first\r\n'
							break
						else:
							## But if the user is authenticated, and it's an external e-mail.
							## we'll notify the parser of such.
							self.parser.external = True
					else:
						if not self.authed_session:
							self.authed_session = '#incomming_externally'
					response += '250 2.1.5 Ok\r\n'

				elif command_to_parse[:4] == 'QUIT':
					response += '221 2.0.0 Bye\r\n'
					self.disconnect = True
					break

				## ==
				## == The following checks are considered AUTHORIZED (logged in) commands:
				## ==
				elif self.authed_session and command_to_parse[:4] == 'DATA':
						self.data_mode = True
						response += '354 End data with <CR><LF>.<CR><LF>\r\n'

				## ==
				## == These checks are only allowed on UN-AUTHED commands,
				## == For instance, AUTH while already authed is considered odd behaviour and
				## == will not be allowed.
				## ==
				elif not self.authed_session and command_to_parse[:4] == 'AUTH':
					response += self.login(command_to_parse)
				else:
					response += '504 need to authenticate first\r\n'
					break

		return response, data

class _clienthandle(Thread):
	def __init__(self, sock, addr):
		self.socket = sock
		self.addr = addr
		self.disconnect = False

		self.parser = parser()
		self.ssl = False

		self.email_catcher = re.compile(r'[\w\-][\w\-\.]+@[\w\-][\w\-\.]+[a-zA-Z]{1,4}')

		Thread.__init__(self)
		self.start()

	def send(self, data):
		if self.ssl:
			self.socket.write(data)
		else:
			self.socket.send(data)

	def run(self):
		recieved_data = ''
		data_mode = False
		while self.disconnect == False:
			try:
				if self.ssl: data = self.socket.read()
				else: data = self.socket.recv(8192)
			except:
				print ' ! ' + str(self.addr[0]) + ' disconnected unexpectedly'
				break

			## To enforce SSL:
			# First we check if we want to enforce SSL via core['_socket']['SSL']
			# then we check if we're in SSL mode or not yet: self.ssl == False
			# then we check if the data we've recieved is NOT: EHLO or STARTTLS, because these two
			# we will allow to bypass the SSL enforcement because EHLO is before the SSL session
			# and STARTTLS starts the SSL session.
			#
			# And to reject anything besides these two commands, we send:
			# - 530 5.7.0 Must issue a STARTTLS command first
			if core['_socket']['SSL'] and self.ssl == False and (data[:4] != 'EHLO' and data != 'STARTTLS'):
				if not 'STARTTLS' in data:
					self.send('530 5.7.0 Must issue a STARTTLS command first\r\n')
					break
				else:
					self.send('220 2.0.0 Ready to start TLS\r\n')
					self.socket = ssl.wrap_socket(self.socket, keyfile=core['SSL']['key'], certfile=core['SSL']['cert'], server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False, cert_reqs=ssl.CERT_NONE, ca_certs=None, ssl_version=core['SSL']['VERSION'])
					self.ssl = True
					self.parser.ssl = self.ssl
					print ' | Converted into a SSL socket!'
					continue

			recieved_data += data
			response, recieved_data = self.parser.parse(recieved_data)

			if len(response) > 0:
				## == Debug:
				##print '>>',[response]
				self.send(response)

				## == Disconnect codes:
				## == If any of these are present in the response,
				## == then we disconnect.
				if '504' in response:
					break
				elif '221' in response:
					break
				elif self.parser.disconnect:
					break
			sleep(0.025)
				
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


sanity_startup_check()

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