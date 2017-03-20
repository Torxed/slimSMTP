#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
import asyncore, re, smtplib, ssl, signal, pwd, grp, pam, psycopg2, psycopg2.extras
import imp, importlib.machinery
from glob import glob
from base64 import b64encode, b64decode
from threading import *
from socket import *
from time import sleep, strftime, localtime, time
from os import _exit, remove, getpid, kill, chown
from os.path import isfile, isdir, abspath, expanduser, basename

__date__ = '2017-03-20 17:00 CET'
__version__ = '0.0.9'
__author__ = 'Anton Hvornum'
pidfile = '/var/run/slim_smtp.pid'
DOMAIN = 'example.com'

core = {'_socket' : {'listen' : '',
					 'ports' : [25, 587]},

		'SSL' : {'enabled' : True,
				 'key' : '/etc/privkey.pem',
				 'cert' : '/etc/cert.pem',
				 'VERSION' : ssl.PROTOCOL_TLSv1}, #|ssl.PROTOCOL_SSLv3},

		'domain' : DOMAIN,

		'supports' : [DOMAIN, 'SIZE 10240000', 'STARTTLS', 'AUTH PLAIN', 'ENHANCEDSTATUSCODES', '8BITMIME', 'DSN'],

		'users' : {b'testuser' : {'password' : '1234'},
					'@POSTGRESQL' : False, # Login via `users` table.
					'@PAM' : pam.pam()},

		'relay' : {'active' : False,
				   'host' : 'smtp.t3.se',
				   'port' : 25,
				   'TLS' : False},

		'external' : {'enforce_tls' : True},

		'storages' : {'testuser@'+DOMAIN : '/home/anton/Maildir/',
					  'default' : '/home/anton/Maildir/',
					  #'@POSTGRESQL' : True, == Auto-loaded via the Plugin support.
					  '@PAM' : False}, # Not possible to store via PAM atm.

		'postgresql' : {'db' : 'database',
						'dbuser' : 'dbuser',
						'dbpass' : 'dbpass'}
		}

__builtins__.__dict__['core'] = core

def log(*args, **kwargs):
	print(' '.join([str(x) for x in args]) + ' ' + ' '.join([str(key) + '=' + str(val) for key, val in kwargs.items()]))

def load_module(m):
	log('[CORE] Loading plugin:', m)
	if isfile('./plugins/'+ m +'.py'):
		namespace = m.replace('/', '_').strip('\\/;,. ')
		#log('    Emulating ElasticSearch via script:',namespace,fullPath.decode('utf-8')+'.py')
		loader = importlib.machinery.SourceFileLoader(namespace, abspath('./plugins/'+ m +'.py'))
		handle = loader.load_module(namespace)
		# imp.reload(handle) # Gotta figure out how this works in Py3.5+
		#ret = handle.main(request=request)

		load_count = 0
		while '@'+m.upper() not in core['storages'] and load_count < 3:
			print(core['storages'])
			sleep(0.2)

		if '@'+m.upper() in core['storages']:
			#x = core['storages'][m]['main_function'](**c['plugins'][m]['parameters'])
			if hasattr(core['storages']['@'+m.upper()], 'setName'):
				core['storages']['@'+m.upper()].setName(m)
			log('[SUCCESS] Module activated.')
		else:
			log('[ERROR] Could not load this module.')

## TODO: Enable multiple queries via subcursors per query() call.
# class postgres(psycopg2):
# 	def __init__(self):
# 
def pg_query(q):
	conn = psycopg2.connect('dbname='+core['postgresql']['db'] +' user='+core['postgresql']['dbuser'] +' password='+core['postgresql']['dbpass'])
	cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
	cur.execute(q)

	if cur.rowcount > 0:
		for row in cur.fetchall():
			yield row
	else:
		yield None

	conn.commit()

	cur.close()
	conn.close()
__builtins__.__dict__['pg_query'] = pg_query

def decompress(b):
	import gzip
	from io import BytesIO
	out = BytesIO(b)
	with gzip.GzipFile(fileobj=out, mode='r') as fh:
			data = fh.read()
	return data.decode('utf-8')

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
			log('Removed the PID file, dead session!')
			remove(pidfile)

	for storages in core['storages']:
		if storages[0] == '@': continue # It's a flag for soft storage links (for instance postgresql)
		if not isdir(core['storages'][storages]):
			log(' ! Warning - Missing storage: ' + core['storages'][storages])
			## TODO: Create these missing folders,
			##       but do it in a clean non-introusive way
			##       (for instance, having default storage to /var would cause issues)

def splitMail(to):
	if '@' in to:
		return to.split('@', 1)
	else:
		return to, None

def getDomainInfo(domain):
	domain = splitMail(domain)[1]
	if not domain: return None
	
	if domain.count('.') > 2:
		domain = '.'.join(domain.rsplit('.',2)[-2:])
	else:
		host = None

	return domain

def save_mail(mail_file, message, account):
	with open(mail_file, 'w') as fh:
		fh.write(message)
	if isfile(mail_file):
		uid = pwd.getpwnam(account).pw_uid
		gid = grp.getgrnam(account).gr_gid
		chown(mail_file, uid, gid)
	return True
__builtins__.__dict__['save_mail'] = save_mail
__builtins__.__dict__['splitMail'] = splitMail
__builtins__.__dict__['getDomainInfo'] = getDomainInfo
__builtins__.__dict__['log'] = log

def local_mail(_from, _to, message):
	mailbox, domain = splitMail(_to)

	if _to in core['storages']:
		log(' | Delivering to local storage: ~/'+mailbox, '(soft-link)')
		mail_file = abspath('{path}/new/{from}-{time}.mail'.format( **{'path' : core['storages'][_to],
																	   'from' : abspath(_from),
																	   'time' : time()} ))

		# TODO: remove ../ form _from
		return save_mail(mail_file, message, mailbox)
	else:
		## Try to query the storage engines that has plugged itself in to us.
		for row in pg_query("SELECT account_backend FROM smtp WHERE mailbox='"+mailbox+"' AND domain='"+domain+"';"):
			delivered = False
			for backend in row['account_backend'].split(','):
				backend = '@'+backend
				if backend in core['storages'] and core['storages'][backend] and core['storages'][backend].store(_from, _to, message):
					delivered = True

			if delivered: return delivered # Might want to pass a obj here later on.

		## As a last resort, store as a default mail.
		log(' | Delivering to local storage: ~/'+_to, '(default-link)')
		path = core['storages']['default'] + '/'
		mail_file = '{path}/new/{from}-{time}.mail'.format(**{'path' : abspath(path),
															  'from' : _from,
															  'time' : time()})

		# TODO: remove ../ form _from
		return save_mail(mail_file, message, mailbox)

def external_mail(_from, to, message):
	import dns.resolver
	for x in dns.resolver.query(getDomainInfo(to), 'MX'):
		try:
			log(' | Trying to deliver externally via MX lookup:', x.exchange.to_text())
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
					log(' ! The relay-server doesn\'t support TLS/SSL!')
					try: server.quit()
					except: pass
					continue # Try the next one
				else:
					log(' ! Could not initated TLS, falling back to PLAIN')
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
			log(' ! Could not relay the mail, Recipient Refused!')
			server.quit()
			return False

		except Exception as e:
			if type(e) == tuple and len(e) >= 3:
				log( ' !- ' + str(e[0]) + ' ' + str(e[1]))
			server.quit()
			return False

		log(' | Delivery done!')
		server.quit()
		return True

	log(' ! No more external servers to try for the domain:', getDomainInfo(to))
	return False

def relay(_from, to, message):
	server = smtplib.SMTP(core['relay'][0], core['relay'][1])
	server.ehlo()
	if core['relay'][2]:
		try:
			server.starttls()
		except:
			log( ' ! The relay-server doesn\'t support TLS/SSL!')
			server.quit()
			return False
	if len(core['relay']) >= 5:
		try:
			server.login(core['relay'][3], core['relay'][4])
		except:
			log( ' ! Invalid credentials towards relay server')
			server.quit()
			return False
	try:
		server.sendmail(_from, to, message)
	except smtplib.SMTPRecipientsRefused:
		log( ' ! Could not relay the mail, Recipient Refused!')
		server.quit()
		return False
	except Exception as e:
		if type(e) == tuple and len(e) >= 3:
			log( ' !- ' + str(e[0]) + ' ' + str(e[1]))
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
		log( ' | Sending mail:',self.From,'(',self.authed_session,') -> ',self.to)
		## == Just to make sure, as long as we're authenticated and the authenticated "user"
		if self.external and self.authed_session:
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
				log(' | Trying login against soft passwords')
				self.authed_session = username
				response += '235 2.7.0 Authentication successful\r\n'
			elif '@POSTGRESQL' in core['users'] and core['users']['@POSTGRESQL']:
				log(' | Trying passwords against postgresql')
				pass
			elif '@PAM' in core['users'] and core['users']['@PAM']:
				log (' | Trying password against PAM')
				if core['users']['@PAM'].authenticate(username, password):
					self.authed_session = username
					response += '235 2.7.0 Authentication successful\r\n'
				else:
					log( ' ! No such user:',[username, '*****']) # password
					# 535 5.7.1 authentication failed\r\n
					response += '535 5.7.8 Error: authentication failed\r\n'					
			else:
				log( ' ! No such user:',[username, '*****']) # password
				# 535 5.7.1 authentication failed\r\n
				response += '535 5.7.8 Error: authentication failed\r\n'
			del password
		elif mode[:5] == 'LOGIN':
			response += '504 Authentication mechanism not supported.\r\n'
		# else:
		# 	## Modular design here XYAUTH (not defined) would auto-load XYAUTH.py as a attempt.
		# 	params = None
		# 	if ' ' in mode:
		# 		mode, params = mode.split(' ',1)
		# 	if isfile(mode+'.py'):
		# 		handle = __import__(mode)
		# 		self.authed_session, response_add = handle.login(params)
		# 		response += response_add
		# 	else:
		# 		response += '504 Authentication mechanism not supported.\r\n'
		# 	del params
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
				if command_to_parse[:4].lower() == 'ehlo':
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

				elif command_to_parse[:4].lower() == 'mail':
					## TODO: Don't assume that the sender actually send a proper e-amil.
					## Also, this list might contain [] because of it.
					self.From = self.email_catcher.findall(command_to_parse)[0]
					response += '250 2.1.0 Ok\r\n'

				elif command_to_parse[:4].lower() == 'rcpt':
					## TODO: Don't assume that the sender actually send a proper e-amil.
					## Also, this list might contain [] because of it.
					self.to = self.email_catcher.findall(command_to_parse)[0]
					to_domain = getDomainInfo(self.to)
					if to_domain != core['domain'] or ('@POSTGRESQL' in core['storages'] and core['storages']['@POSTGRESQL'] and to_domain not in core['storages']['@POSTGRESQL'].getDomains()):
						## If the sender is trying to relay anything except our own domain
						## we'll tell the user to authenticate first.
						if not self.authed_session:
							log(' ! Message to:', self.to, 'is external, but no auth was given.')
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

				elif command_to_parse[:4].lower() == 'quit':
					response += '221 2.0.0 Bye\r\n'
					self.disconnect = True
					break

				## ==
				## == The following checks are considered AUTHORIZED (logged in) commands:
				## ==
				elif self.authed_session and command_to_parse[:4].lower() == 'data':
						self.data_mode = True
						response += '354 End data with <CR><LF>.<CR><LF>\r\n'

				## ==
				## == These checks are only allowed on UN-AUTHED commands,
				## == For instance, AUTH while already authed is considered odd behaviour and
				## == will not be allowed.
				## ==
				elif not self.authed_session and command_to_parse[:4].lower() == 'auth':
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

		Thread.__init__(self)
		self.start()

	def send(self, data):
		## TODO: Convert to bytes in the code instead of here.
		##       This is just as a last resort from the Py2->Py3 conversion.
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
				log( ' ! ' + str(self.addr[0]) + ' disconnected unexpectedly')
				break

			data = data.decode('utf-8') # TODO: Handle bytes data everywhere else instead, less complicated with multilang support

			## To enforce SSL:
			# First we check if we want to enforce SSL via core['SSL']
			# then we check if we're in SSL mode or not yet: self.ssl == False
			# then we check if the data we've recieved is NOT: EHLO or STARTTLS, because these two
			# we will allow to bypass the SSL enforcement because EHLO is before the SSL session
			# and STARTTLS starts the SSL session.
			#
			# And to reject anything besides these two commands, we send:
			# - 530 5.7.0 Must issue a STARTTLS command first
			if core['SSL']['enabled'] and self.ssl == False and (data[:4].lower() != 'ehlo' and data != 'STARTTLS'):
				if not 'STARTTLS' in data:
					self.send(b'530 5.7.0 Must issue a STARTTLS command first\r\n')
					break
				else:
					#self.send(b'250-'+core['domain'] + ' offers a warm welcome.\r\n') # Would want to work this out of the way (only python smtp.sendmail requires this)
					#self.send(b'250 STARTTLS\r\n')
					self.send(b'220 2.0.0 Ready to start TLS\r\n')
					self.socket = ssl.wrap_socket(self.socket, keyfile=core['SSL']['key'], certfile=core['SSL']['cert'], server_side=True, do_handshake_on_connect=True, suppress_ragged_eofs=False, cert_reqs=ssl.CERT_NONE, ca_certs=None, ssl_version=core['SSL']['VERSION'])
					self.ssl = True
					self.parser.ssl = self.ssl
					log( ' | Converted into a SSL socket!')
					continue

			recieved_data += data
			if len(recieved_data) == 0: break # TODO: Debug if this is OK
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
			log(' ! Could not bind main socket in 30 seconds, exiting.')
			return False

		log( ' | Bound to ' + ':'.join((listen, str(port))))

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
			log(' ?', na, 'has connected')

			ns.send(b'220 ' + bytes(core['domain'], 'UTF-8') + b' ESMTP SlimSMTP\r\n')
			ch = _clienthandle(ns, na)
			sleep(0.025)
		self.close()

sanity_startup_check()

pid = getpid()
f = open(pidfile, 'w')
f.write(str(pid))
f.close()

for file in glob('./plugins/*.py'):
	load_module(basename(file).split('.')[0])

for port in core['_socket']['ports']:
	s = _socket(core['_socket']['listen'], port)

signal.signal(signal.SIGINT, signal_handler)
while 1:
	sleep(1)