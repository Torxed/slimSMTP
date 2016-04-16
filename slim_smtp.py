#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
import asyncore, re, smtplib, ssl, signal, pwd, grp, pam #psycopg2
from base64 import b64encode, b64decode
from threading import *
from socket import *
from time import sleep, strftime, localtime, time
from os import _exit, remove, getpid, kill, chown
from os.path import isfile, isdir, abspath

__date__ = '2013-07-10 09:46 CET'
__version__ = '0.0.7p2'
pidfile = '/var/run/slim_smtp.pid'
DOMAIN = 'example.com'

core = {'_socket' : {'listen' : '', 'ports' : [25, 587]},
		'SSL' : {'enabled' : True, 'key' : '/etc/ssl/hvornum.se.key_nopass', 'cert' : '/etc/ssl/hvornum.se.crt', 'VERSION' : ssl.PROTOCOL_TLSv1},#|ssl.PROTOCOL_SSLv3},
		'domain' : DOMAIN,
		'supports' : [DOMAIN, 'SIZE 10240000', 'STARTTLS', 'AUTH PLAIN', 'ENHANCEDSTATUSCODES', '8BITMIME', 'DSN'],
		'users' : {b'testuser' : {'password' : '1234'}, '@POSTGRESQL' : False, '@PAM' : pam.pam()},
		'relay' : {'active' : False, 'host' : 'smtp.t3.se', 'port' : 25, 'TLS' : False},
		'external' : {'enforce_tls' : True},
		'storages' : {'anton@'+DOMAIN : '/home/anton/Maildir/',
					'default' : '/home/anton/Maildir/'}}

class SanityCheck(Exception):
	pass

def pid_exists(pid):
	"""Check whether pid exists in the current process table."""
	if pid < 0:
		return False
	try:
		kill(pid, 0)
	except ProcessLookupError as e:
		return False
	except OSError as e:
		return e.errno == errno.EPERM
	else:
		return True

def signal_handler(signal, frame):
	try:
		s.close()
	except:
		pass
	remove(pidfile)
	_exit(1)

def sanity_startup_check():
	if core['SSL']['enabled']:
		if not isfile(core['SSL']['key']):
			raise SanityCheck('Certificate error: Missing Key')
		if not isfile(core['SSL']['cert']):
			raise SanityCheck('Certificate error: Missing Cert')

	if isfile(pidfile):
		with open(pidfile) as fh:
			thepid = fh.read()
			if len(thepid) == 0:
				thepid = '-1'
			thepid = int(thepid)
		if pid_exists(thepid):
			exit(1)
		else:
			print('Removed the PID file, dead session!')
			remove(pidfile)

	for storages in core['storages']:
		if not isdir(core['storages'][storages]):
			print(' ! Warning - Missing storage: ' + core['storages'][storages])
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

def splitMail(to):
	return to.split('@', 1)

def local_mail(_from, _to, message):
	if _to in core['storages']:
		path = core['storages'][_to] + '/'
	elif '@POSTGRESQL' in core['storages']:
		conn = psycopg2.connect("dbname=DB user=DBUSER password=DBPASSWORD")
		cur = conn.cursor()
		cur.execute("CREATE TABLE IF NOT EXISTS newtable (id bigserial PRIMARY KEY, mailbox varchar(255), domain varchar(255), account varchar(20));")
		user, domain = splitMail(to)

		cur.execute("SELECT * FROM newtable WHERE ")

		#>>> cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)",
		#...      (100, "abc'def"))

		# Query the database and obtain data as Python objects
		#>>> cur.execute("SELECT * FROM test;")
		#>>> cur.fetchall()
		#(1, 100, "abc'def")
	else:
		path = core['storages']['default'] + '/'

	# TODO: remove ../ form _from
	mail_file = abspath(path + '/new/') + '/' + _from + '-' + str(time()) + '.mail'

	with open(mail_file, 'w') as fh:
		fh.write(message)

	if isfile(mail_file):
		uid = pwd.getpwnam("torxed").pw_uid
		gid = grp.getgrnam("torxed").gr_gid
		chown(mail_file, uid, gid)

	return True

def external_mail(_from, to, message):
	import dns.resolver
	for x in dns.resolver.query(getDomainInfo(to)[1], 'MX'):
		try:
			print(' | Trying to deliver externally via MX lookup:', x.exchange.to_text())
			server = smtplib.SMTP(x.exchange.to_text().rstrip('\\.,\'"\r\n '), 587, timeout=5)
			server.ehlo()
			server.starttls()
		except:
			try:
				server = smtplib.SMTP(x.exchange.to_text().rstrip('\\.,\'"\r\n '), 25, timeout=5)
				server.ehlo()
				server.starttls()
			except:
				if core['external']['enforce_tls']:
					print(' ! The relay-server doesn\'t support TLS/SSL!')
					try: server.quit()
					except: pass
					continue # Try the next one
				else:
					print(' ! Could not initated TLS, falling back to PLAIN')
					try: server.quit()
					except: pass
					try:
						server = smtplib.SMTP(x, 25, timeout=5)
						server.ehlo()
					except:
						try: server.quit()
						except: pass
						continue

		try:
			server.sendmail(_from, to, message)
		except smtplib.SMTPRecipientsRefused:
			print(' ! Could not relay the mail, Recipient Refused!')
			server.quit()
			return False

		except Exception as e:
			if type(e) == tuple and len(e) >= 3:
				print( ' !- ' + str(e[0]) + ' ' + str(e[1]))
			server.quit()
			return False

		print(' | Delivery done!')
		server.quit()
		return True

	print(' ! No more external servers to try for the domain:', getDomainInfo(to)[1])
	return False

def relay(_from, to, message):
	server = smtplib.SMTP(core['relay'][0], core['relay'][1])
	server.ehlo()
	if core['relay'][2]:
		try:
			server.starttls()
		except:
			print( ' ! The relay-server doesn\'t support TLS/SSL!')
			server.quit()
			return False
	if len(core['relay']) >= 5:
		try:
			server.login(core['relay'][3], core['relay'][4])
		except:
			print( ' ! Invalid credentials towards relay server')
			server.quit()
			return False
	try:
		server.sendmail(_from, to, message)
	except smtplib.SMTPRecipientsRefused:
		print( ' ! Could not relay the mail, Recipient Refused!')
		server.quit()
		return False
	except Exception as e:
		if type(e) == tuple and len(e) >= 3:
			print( ' !- ' + str(e[0]) + ' ' + str(e[1]))
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
		self.disconnect = False

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
		print( ' | Sending mail:',self.From,'(',self.authed_session,') -> ',self.to)
		## == Just to make sure, as long as we're authenticated and the authenticated "user"
		## == doesn't begin with an "#" (reserved for system-design-users), we'll send externally.
		if self.external and self.authed_session and self.authed_session[0] != '#':
			if external_mail(self.From, self.to, self.data + '\r\n.\r\n'):
				self.reset()
				return '250 2.0.0 Ok: queued as ' + b64encode(bytes(str(time()), 'UTF-8')).decode('utf-8') + '\r\n'
		elif self.external and not self.authed_session:
			return '504 need to authenticate first\r\n'
		elif not self.external:
			local_mail(self.From, self.to, self.data)
			self.reset()
			return '250 2.0.0 Ok: Delivered\r\n'
		
		return '550 Could not deliver the e-mail\r\n'

	def login(self, data):
		trash, mode = data.split(' ',1)
		response = ''
		if mode[:5] == 'PLAIN':
			mode, password = mode.split(' ',1)
			authid, username, password = b64decode(bytes(password, 'UTF-8')).split(b'\x00',2)

			if username in core['users'] and core['users'][username]['password'] == password:
				self.authed_session = username
				response += '235 2.7.0 Authentication successful\r\n'
			elif '@POSTGRESQL' in core['users'] and core['users']['@POSTGRESQL']:
				# Connect to an existing database
				#>>> conn = psycopg2.connect("dbname=test user=postgres")

				# Open a cursor to perform database operations
				#>>> cur = conn.cursor()

				# Execute a command: this creates a new table
				#>>> cur.execute("CREATE TABLE test (id serial PRIMARY KEY, num integer, data varchar);")

				# Pass data to fill a query placeholders and let Psycopg perform
				# the correct conversion (no more SQL injections!)
				#>>> cur.execute("INSERT INTO test (num, data) VALUES (%s, %s)",
				#...      (100, "abc'def"))

				# Query the database and obtain data as Python objects
				#>>> cur.execute("SELECT * FROM test;")
				#>>> cur.fetchone()
				#(1, 100, "abc'def")
				pass
			elif '@PAM' in core['users'] and core['users']['@PAM']:
				if core['users']['@PAM'].authenticate(username, password):
					self.authed_session = username
					response += '235 2.7.0 Authentication successful\r\n'
				else:
					print( ' ! No such user:',[username, '*****']) # password
					# 535 5.7.1 authentication failed\r\n
					response += '535 5.7.8 Error: authentication failed\r\n'					
			else:
				print( ' ! No such user:',[username, '*****']) # password
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
							self.external = True
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
				sleep(0.025)

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
		if type(data) == str:
			data = bytes(data, 'UTF-8')

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
				print( ' ! ' + str(self.addr[0]) + ' disconnected unexpectedly')
				break

			data = data.decode('utf-8') # TODO: Handle bytes data everywhere else instead, less complicated with multilang support

			## To enforce SSL:
			# First we check if we want to enforce SSL via core['_socket']['SSL']
			# then we check if we're in SSL mode or not yet: self.ssl == False
			# then we check if the data we've recieved is NOT: EHLO or STARTTLS, because these two
			# we will allow to bypass the SSL enforcement because EHLO is before the SSL session
			# and STARTTLS starts the SSL session.
			#
			# And to reject anything besides these two commands, we send:
			# - 530 5.7.0 Must issue a STARTTLS command first
			if core['SSL']['enabled'] and self.ssl == False and (data[:4] != 'EHLO' and data != 'STARTTLS'):
				if not 'STARTTLS' in data:
					self.send(b'530 5.7.0 Must issue a STARTTLS command first\r\n')
					break
				else:
					self.send(b'220 2.0.0 Ready to start TLS\r\n')
					self.socket = ssl.wrap_socket(self.socket, keyfile=core['SSL']['key'], certfile=core['SSL']['cert'], server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False, cert_reqs=ssl.CERT_NONE, ca_certs=None, ssl_version=core['SSL']['VERSION'])
					self.ssl = True
					self.parser.ssl = self.ssl
					print( ' | Converted into a SSL socket!')
					continue

			recieved_data += data
			response, recieved_data = self.parser.parse(recieved_data)

			if len(response) > 0:
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
	def __init__(self, listen, port):
		socket.__init__(self)

		for i in range(6):
			try:
				self.bind((listen, port))
				self.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
				break
			except:
				sleep(5)

		try:
			self.listen(4)
		except:
			print(' ! Could not bind main socket in 30 seconds, exiting.')
			return False

		print( ' | Bound to ' + ':'.join((listen, str(port))))

		Thread.__init__(self)
		self.start()

	def run(self):
		while 1:
			try:
				ns, na = self.accept()
			except:
				break

			if not 'clients' in core:
				core['clients'] = {}

			core['clients'][str(na[0]) + ':' + str(na[1])] = {'socket' : ns, 'address' : na}
			print(' ?', na, 'has connected')

			ns.send(b'220 ' + bytes(core['domain'], 'UTF-8') + b' ESMTP SlimSMTP\r\n')
			ch = _clienthandle(ns, na)
			sleep(0.025)
		self.close()

sanity_startup_check()

pid = getpid()
f = open(pidfile, 'w')
f.write(str(pid))
f.close()

for port in core['_socket']['ports']:
	s = _socket(core['_socket']['listen'], port)

signal.signal(signal.SIGINT, signal_handler)
while 1:
	sleep(1)