#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
import asyncore, re, smtplib, ssl, signal, pwd, grp, pam, psycopg2, psycopg2.extras
from base64 import b64encode, b64decode
from threading import *
from socket import *
from time import sleep, strftime, localtime, time
from os import _exit, remove, getpid, kill, chown
from os.path import isfile, isdir, abspath, expanduser


__date__ = '2016-04-17 23:59 CET'
__version__ = '0.0.8'
pidfile = '/var/run/slim_smtp.pid'
DOMAIN = 'example.com'

core = {'_socket' : {'listen' : '', 'ports' : [25, 587]},
		'SSL' : {'enabled' : True, 'key' : '/etc/ssl/hvornum.se.key_nopass', 'cert' : '/etc/ssl/hvornum.se.crt', 'VERSION' : ssl.PROTOCOL_TLSv1},#|ssl.PROTOCOL_SSLv3},
		'domain' : DOMAIN,
		'supports' : [DOMAIN, 'SIZE 10240000', 'STARTTLS', 'AUTH PLAIN', 'ENHANCEDSTATUSCODES', '8BITMIME', 'DSN'],
		'users' : {b'testuser' : {'password' : '1234'}, '@POSTGRESQL' : False, '@PAM' : pam.pam()},
		'relay' : {'active' : False, 'host' : 'smtp.t3.se', 'port' : 25, 'TLS' : False},
		'external' : {'enforce_tls' : True},
		'storages' : {'testuser@'+DOMAIN : '/home/anton/Maildir/',
					'default' : '/home/anton/Maildir/',
					'@POSTGRESQL' : True,
					'@PAM' : False},
		'postgresql' : {'db' : 'example', 'dbuser' : 'example', 'dbpass' : 'example'}
		}

def decompress(b):
	import gzip
	from io import BytesIO
	out = BytesIO(b)
	with gzip.GzipFile(fileobj=out, mode='r') as fh:
			data = fh.read()
	return data.decode('utf-8')

## Decompile helpers.source
compile(decompress(b'\x1f\x8b\x08\x00\x0e\x04\x14W\x02\xff\xcdYmo\xe3\xb8\x11\xfel\x03\xfd\x0f\xb3\xd9\x0f\x94\x1bG\xd9\xdd\xbbE\x8b\xb4>\\\x90\xe4\xaeA\x93M.\x0ep\x07\xa4\x86AK\xb4MD\x16\xb5$\x15\xc7@q\xbf\xbd3$%K~I\x93n\x0b\xd4\x1f\xb2\x1493\x9c\x97g\x86Cn7\xc9\xb810\xe4\xb9\xb4\xab\xb3\xb9H\x1e\xa3\x8b\xe7D\x14V\xaa\xbcw\xd2\xed\x14\xb8\xda\xed\xa6b\n\x85L\xc7\xe2Y\x1ak"\x1c\xd2\xda\xc1\xc1\x81\xe3\x80\xe5\\\xd8\xb9\xd0D\x02\x9e\x04d\x0e8\x05I\xa9\xb5\xc8-\x14Z%\x02\xf7\xb1|\x92\x89\x18\x19\xbb\x1d\xe9D\xc2_\xe1\x03\x8a\xeahaK\x9d\xc3O<3\xa2\xdb\xb1zE\x93\x8f2\xcbh\xb3>|\xe8u;\xc2\xe9\x05\xb7^\xd4\x95R\x8feq\xa1\xb5\xd2\xc0\r\x88m!\x81\xfef\xb8\x93H\xc4B\xeb\\\xc1`\x00n\x10_\xdc^\xdc]#\x17\xf26\xc8\xeeu)\xbc\xfdF\xcer\x9e\x8d\xe7<O3\xa1#\xff\xd9\x87\xa9\xe6\x0bA\xde\x08:\x9b8\xc9\x94\x11Q\xad0M:/\xa2\xc8\x85z\x12d\xd0Tf\x02\t\xc8\x9f6\xfa\xd8\x0b\x1b\xb8\x18\x8c\x8d\xe5\xda\x96\xc58q\xc1 \xc9\xe8\xa9Di\xf1\xc0\x86\xc3+6z`"\'/\xa6lD\xa2q1W\x16\xa4!\x99Q\x8b\xeeQ\xac\xd8\x88\x04\xa05\\\x1a\xd1\x8a2;\x13\xda\xca\xa9L\xb8\x15\xe4\x01\xa5O\xe0Z\x1a#\xf3\x19\xfc\x1d\x19{/\xcbN\x90\xfb?\x13NK(\xdd\x99\x15$W\x1e!iKi\xe7\xa0\n\x91\xd7\xb3\x14\xb9\xe9\xdc\xed\x84\x90"\xcc\x0c\xf0;\xd6\x82\xa7\xe4e\xa7f\x86\xf4~\xb1G\x11u\x90j\x90\xb3\xa3\x8f\xac\xc5/s[\xd1{;\x1b\xe8\x0e\xf3ND\x15\xa0N\x8d\x8bN\xa1\x89\x99\xdd\xb9`\xa6\x0e\xe5\xb7\x97\xe7@\xaa\xf6!E\xa5\xc0 <1}\xde9\x1fnE\xbd\xdb\x99"\x1a\x8dU\x9a\xcf\x84K\x14\xef\xd8j\xa6\x0ek5\xf1\xf0aD6\xb1\x1f\xd9\t\x92\xe6V\xe6\xa5\x80\xf7pi\x99\x01\x0e\xd3\x8c\xcf\xc0ITS[\xf1@&\xf3G\x03\x11\xcd\xcb\x1c\x11\x95\'\x02\ne\xecL\x0b\xf35k\xc56\x95:\xda\xd4\xe0\xa1\x1a\x86\x08\x07\x9b\xe1\x1d\xfc\xcauNQ<\xaa\xe3\x19HO\x80\xc1!\xbc \x88\xe4\xbc\x7f\x0f\xf77\xe77\'p\x86\xd1Ch\xa0\xf3\x109\x8b i\xaa\xb2Th\xd3\x0f\x94\xfe7)-\xa4\n\xa4%OqH2\xc1s\xd4<?B\x8d\xb4*\x8d|\x12\xb0\xe4\xab\x16O\xcb\xee>\xcc\xf9\x13\x89\xc7\x1c\xe3e\xb6\xf6\x91Up\xfc\xc45,U\x99\xa5\x90\xf0\x12UAMJaBB\xce\x84=W\x0b.\xf3\xcb|\xaa\xa2\xd4\rC>b0H\x1f?G.\xf2#D\x96\x1f\xc4\xa6\xc8\x109H\xd6\xff\xd8{\xf88\xeav\x1c[XLTI\xee\x8cY\x0f~\x80O\xc4>\xc7\xd8\xf4a\x8f\x90\x98\x84\xac+\x13\xd1"\xcd\x17\x95ce\xaa\xeaTS@(\'\xc4|\xcde\x16YEZ\x07B\xab\x1a\xba\xc1\xba\xf6<\x89\xf1\x82\x88\xe9\xcf\xd8\x83y\x818FG\xf5\x81\'Nc\x92\xb2N\xcf\x06![\xb2F\x96bn.\xb5\xb4"\n\xfc\xbdf\xaa\xd7\\\x0eX\xa5K\xc6b\x99\xc6\xe8\xebb\x99\xf3ET\xed\x15\x17\xcb1.#\xd1\xcc\x11\xcdtAD3\xdd"\x9a\xe9\xf1\xcc\x11%s\xb5l\xe9T\xd2\xb11\xa3\xfc\xaec9\xf1\xd14\xae\xa8b&\x91\xa7\x0b\xb3JT1\xfb\x14\xd3\xb7H\xd0-\xe9\x04w\x10\x03v\xe8\xb1\\e\r\x15\xbdt\xc2Fp\xc8\x00\x91\xa2\xf7\x10\xd0\x92\'\xa2\x9a\xbfT:\xddCH\xcb\x8c\xb2\x02\x8fH\xd4\x83\xb6\x8fqh\x14f\xa3\xfbg<\xe5\t"u5\xa8U\x14\xcfVs\x13\x9f\xcb\xc4\x9e9\x12\xcf\x8d\xf3")\xd1\xdf\x07\xc3\x8b\xab\x8b\xb3\xfb\nF?\xdd\xdd\\\x83Y\xd8\xe2/\x07=\n\xbfA\xf0\x1b\xdc\xeaa\xe4K\x90VKW}P\xc2T\xd8d\xce\xf1\xb0\xed\x85\xda\x83k\xa8\xa4\x93\x83\xd6 U`_W wD\xba\xb9\x98\x17\x88\x874j\xf1\x04\xd5\xea\xb3\xd0\xdbW}\x05,\x06\x01>B\x99J\xf0xu\x18\x1cO\xb5Z\xf4alU\rBR\x8c\xd6&\xea\xb9\x91\'k\x8c#m8Sp\xb4\xaf\xa8Ve\xec\x9fp.2,\x1c\x9a\xca\x02\x92\xbb\xad\xd7\x85\xec\xf7cv\xe8\xf6f\x11\x15\xd5#*\xa6=W\xcc\x0b\x8e\xe8\x1flW9\xa4\xc6\x98\x03;\xa6S\xa6\x06!R\xf2\x89!\x9e\xc81\x12A.\x96\xc7\x98,\x8e\x16\xff:K\xe9\xeb\x88\xbe\x8c\xd5\x91\x95\x0bt\x91\xa3\x88I\x12C\xab:U\xd9\xf4g\t\xc4\xf11\x95\xfc\x85g\xa7\xa6\xe3\xc5\xf4\r~#\xff\xa0\xd9T\xbcno\x86\xf7?\xdf]\x0c\x7f\xb9b\xbb|\x05\xd8\xe3l\x1b\xd9bs\xfe\xfc\xbf\xc9\xa1oK"\xe7\xe0\rp\xf5\xa1\xaaz\xe3\tO\x1e\x11\xdf\x8e\x8a\xe7V\xe5t\xc4\xcc\xe6h\xed\x02\x07\xb7\xa7\xd7\xed\x95\x1f\x877g\x97\xa7W\x00\xa7W\x97\xa7C\xb7\x86J\x88\t\xf6\xabk\xae@\xe4V-\xd6T\x8b\xdd3\xae\x86\xf3k\xbd\xba+\xbd\xff\xb8\xcel\xf8\xf5o\x17w\x17\x95\xee\x03vp\x18\x86\x87\x07\x0cN\xbf\x9c\x07ch\xc1\x8fp\xdeU\x83\x97\x0b@]\x016\\\xc0|#\x82&3\xdf`\xbd=\xa1\x1aM\x88o\x8fv\xa6\x8bx.\x10\x82\x84\x83\x88\xfd\xce\x0e\x9d.\xc12\x8c\xb7\xcb\x1e\xcazl]|B\xbd.\x93\xfc~/\xe7\xca\xc6V]\xd7\x04f{\xfd\xd1\xe8\xcd\x9c\xf0*Q\xcfU\xce,\xe5(\x9e;\xe4\x10\xd7\xccC`\x1b\x071\xc0gt\x1caGRN<\\\xab\x8a\xf8.\x08\xf3\xbf\x93\xde\x8b\xce6s\xae\xb1\x11\rJ\x9f\xb0M#v\xbb\xbd\x96\x86\x9d\x9cXL\xb0\xef:\xa9\x1c\xe4\xb4\xf9\x863\xa9\x96\xf1\n\xe8\xae\x01\xba\xdb\xc15`=dQn@m\xd8a\x03\xb8M/\xe1\x0f}\xe19\x1a\xee8\xc4`\x1dn\x9eU\xaf\x04\xe2\x96\xb0o\xc4\xe2\xbf\x01\xe3\xf6vM\xe7\xd6\xa7ig\xe3\xaby\xd4\xae\xdb\xc6\xb7\xe7jh\x98_q\xfe\xb1@\xca\xfe\x87\xa7\xe0\x7f\xf3\x18\xdc\xba\xdc#\x8c\x85\xce7\xfa\x8f\x8d\xf6C.\n\xa5\xf12\x92\x1b\xbc{\x1a\x95\xa1\x0b}#\xf5\xec\xae\x02\x8d\xe9\xf8k)\xf4*j\xdf\x1f\xb0A\xc1\x8b\x00\xfa\xf5\xfa7\xe6\xc0\x1a\x1e\x0c\x1a\x81\xb9\xd7\xab\x10\x94\xd4\x87\xa8\xd6+[\xc1\x93\xe4p\xfd\x1b\x86\x8b\xde=(\xcb\x9f1\xbd\x10\xfb\xf9L\xc4V\x8d-\x92\xa2\xc7H \xa2\x95x\x07.\xcf29\x89\x87\xd7\xf7\xb7\xd1.\xf2X\xa3\xb3e\x11\xb1\x7f\xc4}v\xf0\x87.\xb0^\x1f>\xff\xf9Oh;\x06@\x95v\xf0\xb9!1\x16\xf3LE\xcd\t\xf7Va3\xe3&\xd7\xcf\x1d\xb5i\xdf\xaa\xca\xa7\xcf\x9b\x9al\xab\xb2S\x97\xa62\xeb\xf7\x93\xca\x9b\xfe\x11\x05C\x97\x881r\xf8f\xa6u\xcd\xbd\xc7[\xbd\x16\x19_\x1d\x05\x0bR%\x0c\x95tS\x16\x0e\x05\xf7W\xc3\xe3\xe1\xf0\xea]\x95\xc8d1\x04M\xbe\x96x\xbd\n\xf3A\x0f\xf0/@\xf4k\\\xe11\xde\xee\xfd G\xc5\x80\xaes\x8e\xa3zhh\xeas\xe6\xee\xa8\xee\xc2\x9eK\x8bW\xe7\x944\xe8cg\x91e\x04\x19\xaa\x97\x84\x9b\xdb\xab\xd3\xcb/o\xd7\xa9\x8e\xd7\xde\x88\xed\x8c\xc5\xaeh\xb4<\xbf_\x87\x1dJ\xd4\x9e\xe96\x92\xa3\n.\x1e\x06\xfbR\xb3\x86^K\xe5;\x91\xc8B\x8a\xdc\x9a;1\xc5\x02\x9en<d\xac=\xea\xe2\xec\xe2@;\xf4\xa1\xe6\x84\xc0\x19\x82\xbceE\xeb\xb9q\xadE\xfd~Z?9\x12\x02\xed\xaa\x10\x91p\xafS\xb6,\xb0,R\x8fM\xcfV8\xf7\xc3\x00\xbek6T\x80\n\x1eAU\x0b\x056\x19\xae\x126f>\x8ez\xaf\xd3i\xab\xea\xaf\x10\xca\xb9\xf0&mr\xb7\xcab\xc3W_\x14,0\x81\xeaj\x14\x02j\x08q\x18(\xf7\xfcD\xfe\x0b\xcf!X\x9bv\x95\xbe\xf5\xbd/hG\x85\xd79\x7fO\xc1\xdd\rE\x9f\xca\x8e\xcf\xf5_}h\xcf\xb8\x8d6pYW\x80\x8a\xe8\xd3\xe8d\x07\xc8\xf6T\xb3uP\xdeZ\x17^\x0eO\xf5p\xd9R\xcd\xa1\xe1\xf3\x0e\xed25\x93\x1b\xb4\x0f\xdfmY\xff\xfdh\xbf\xf2\x97\xf9\x13\xcf$\xde\xec\xb0]DxKT\x02]\xbe\xe4:5!\t\xfcV\xaf\xd2\xbdz\xee~M~\xbe6=\x1b\xba\xbe9=\xf7`\xb9\xfd\x7f\x01\xdb\xa9\xf9\xda\xcc|cb\xbe\xa8Mws\xb9\x99w\xff\x02\xc9R\xf6\x87\x91\x19\x00\x00'), '', 'exec')

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
				print(' | Trying login against soft passwords')
				self.authed_session = username
				response += '235 2.7.0 Authentication successful\r\n'
			elif '@POSTGRESQL' in core['users'] and core['users']['@POSTGRESQL']:
				print(' | Trying passwords against postgresql')
				pass
			elif '@PAM' in core['users'] and core['users']['@PAM']:
				print (' | Trying password against PAM')
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
					to_domain = getDomainInfo(self.to)[1]
					if to_domain != core['domain'] or ('@POSTGRESQL' in core['storages'] and core['storages']['@POSTGRESQL'] and to_domain in getDbDomains()):
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
				print( ' ! ' + str(self.addr[0]) + ' disconnected unexpectedly')
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