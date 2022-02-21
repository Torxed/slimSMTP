import pydantic
import logging
import ssl
import base64
from pam import pam as pamd
from typing import List, Iterator
from .parser import Parser
from ..realms import Realm
from ..sockets import Client
from ..exceptions import AuthenticationError, InvalidAddress
from ..logger import log

class CMD_DATA(pydantic.BaseModel):
	data: str
	realms: List[Realm]
	session: Client


# class authenticated:
# 	def __init__(self, func :Callable[..., Any], **kwargs :str):
# 		if type(func).__name__ == 'type':
# 			self.func = func

# 			return None

# 		if func.obj.session.authenticated == False:
# 			raise AuthenticationError(f"Session({func.session}) is not authenticated and can not perform CMD({func})")

# 	def can_hanadle(self, obj :CMD_DATA):
# 		return self.func.can_hanadle(obj)

# 	def handle(self, obj :CMD_DATA):
# 		for result in self.func.respond(obj):
# 			yield result


class MAIL_FROM:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return obj.data.lower().startswith('mail from:')

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		log(f"Processing: MAIL_FROM", level=logging.DEBUG, fg="cyan")
		from ..mail.helpers import clean_email
		try:
			obj.session.mail.add_sender(clean_email(obj.data.lower()[10:].strip()))
		except InvalidAddress:
			obj.session.set_parser(
				Parser(
					expectations=[
						QUIT
					]
				)
			)
			return None

		yield b'250 Ok\r\n'

		obj.session.set_parser(
			Parser(
				expectations=[
					RCPT_TO,
					QUIT
				]
			)
		)

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in MAIL_FROM.respond(obj):
			yield result


class RCPT_TO:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return obj.data.lower().startswith('rcpt to:')

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		log(f"Processing: RCPT_TO", level=logging.DEBUG, fg="cyan")

		from ..mail.helpers import clean_email
		try:
			obj.session.mail.add_recipient(clean_email(obj.data.lower()[8:].strip()))
		except AuthenticationError:
			parser_list = [
				QUIT
			]

			if isinstance(obj.session.socket, ssl.SSLSocket):
				parser_list.append(AUTH_PLAIN)

			obj.session.set_parser(
				Parser(
					expectations=parser_list
				)
			)

			yield b'504 need to authenticate first\r\n'
			return None

		yield b'250 Ok\r\n'

		obj.session.set_parser(
			Parser(
				expectations=[
					RCPT_TO,
					DATA,
					QUIT
				]
			)
		)

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in RCPT_TO.respond(obj):
			yield result


class MAIL_SESSION:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return True

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		if obj.data == '.':
			log(f"Processing: DATA (completion)", level=logging.DEBUG, fg="cyan")
			if obj.session.parent.configuration.storage.store_email(obj.session):
				yield b'250 Ok: Queued!\r\n'

				obj.session.set_parser(
					Parser(
						expectations=[
							QUIT
						]
					)
				)
			else:
				obj.session.set_parser(
					Parser(
						expectations=[
							QUIT
						]
					)
				)
				return None
		else:
			log(f"Processing: DATA (transit)", level=logging.DEBUG, fg="cyan")
			obj.session.mail.add_body(obj.data)

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in MAIL_SESSION.respond(obj):
			yield result


class DATA:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return obj.data.lower().startswith('data')

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		log(f"Processing: DATA", level=logging.DEBUG, fg="cyan")

		yield b'354 End data with <CR><LF>.<CR><LF>\r\n'

		obj.session.set_parser(
			Parser(
				expectations=[
					MAIL_SESSION
				]
			)
		)

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in DATA.respond(obj):
			yield result


class EHLO:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return obj.data.lower().startswith('ehlo')

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		log(f"Processing: EHLO", level=logging.DEBUG, fg="cyan")

		supports = [
			obj.realms[0].fqdn,
			'PIPELINING',
			'SIZE 10485760',
			'ENHANCEDSTATUSCODES',
			'8BITMIME'
		]

		if isinstance(obj.session.socket, ssl.SSLSocket):
			# We enable LOGIN only when we're processing a ssl.SSLSocket
			supports.append('AUTH PLAIN LOGIN')
		else:
			supports.append('STARTTLS')

		response = b''
		for index, support in enumerate(supports):
			if index != len(supports) - 1:
				response += bytes(f"250-{support}\r\n", 'UTF-8')
			else:
				response += bytes(f"250 {support}\r\n", 'UTF-8')

		yield response

		expectation_list = [
			MAIL_FROM,
			QUIT
		]

		if isinstance(obj.session.socket, ssl.SSLSocket):
			expectation_list.append(AUTH_PLAIN)
		else:
			# We only add STARTTLS if the endpoint is a socket, not ssl.socket
			expectation_list.append(STARTTLS)

		obj.session.set_parser(
			Parser(
				expectations=expectation_list
			)
		)

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in EHLO.respond(obj):
			yield result


class PLAIN_CREDENTIALS:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return True

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		credentials = obj.data.strip()
		if len(credentials):
			username, password = base64.b64decode(credentials).strip(b'\x00').split(b'\x00', 1)
			username = username.decode('UTF-8')
			password = password.decode('UTF-8')
			# password = base64.b64encode(password)

			pam = pamd()
			if pam.authenticate(username, password):
				log(f"Client(address={obj.session.address}) authenticated as {username}", level=logging.INFO, fg="green")
				obj.session.parent.clients[obj.session.fileno].authenticated = True

				obj.session.set_parser(
					Parser(
						expectations=[
							MAIL_FROM,
							QUIT
						]
					)
				)
				
				yield b'235 Authentication succeeded\r\n'
				return

		obj.session.spammer(f"Client(address={obj.session.address}) failed authentication as {username}")
		# obj.session.set_parser(
		# 	Parser(
		# 		expectations=[
		# 			QUIT
		# 		]
		# 	)
		# )

		# yield b'535 5.7.8 Error: authentication failed.\r\n'

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in PLAIN_CREDENTIALS.respond(obj):
			yield result


class AUTH_PLAIN:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return obj.data.lower().startswith('auth plain')

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		log(f"Processing: AUTH PLAIN", level=logging.DEBUG, fg="cyan")

		credentials = obj.data[10:].strip()
		if len(credentials):
			username, password = base64.b64decode(credentials).strip(b'\x00').split(b'\x00', 1)
			username = username.decode('UTF-8')
			password = password.decode('UTF-8')
			# password = base64.b64encode(password)

			pam = pamd()
			if pam.authenticate(username, password):
				log(f"Client(address={obj.session.address}) authenticated as {username}", level=logging.INFO, fg="green")
				obj.session.parent.clients[obj.session.fileno].authenticated = True

				obj.session.set_parser(
					Parser(
						expectations=[
							MAIL_FROM,
							QUIT
						]
					)
				)
				
				yield b'235 Authentication succeeded\r\n'
			else:
				# obj.session.set_parser(
				# 	Parser(
				# 		expectations=[
				# 			QUIT
				# 		]
				# 	)
				# )
				# yield b'535 5.7.8 Error: authentication failed.\r\n'

				obj.session.spammer(f"Client(address={obj.session.address}) failed authentication as {username}")

		else:
			obj.session.set_parser(
				Parser(
					expectations=[
						PLAIN_CREDENTIALS
					]
				)
			)

			yield b'334\r\n'

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in AUTH_PLAIN.respond(obj):
			yield result


class STARTTLS:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return obj.data.lower().startswith('starttls')

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		log(f"Processing: STARTTLS", level=logging.DEBUG, fg="cyan")
		yield b'220 2.0.0 Ready to start TLS\r\n'

		import ssl
		protocol = obj.session.parent.configuration.tls_protocol
		ssl_context = ssl.SSLContext(protocol=protocol if protocol else ssl.PROTOCOL_TLSv1_2)
		ssl_context.load_default_certs()
		ssl_context.verify_mode = ssl.CERT_NONE
		ssl_context.load_cert_chain(
			certfile=str(obj.session.parent.configuration.tls_cert),
			keyfile=str(obj.session.parent.configuration.tls_key)
		)
		for ca in obj.session.parent.configuration.tls_certificate_authorities:
			ssl_context.load_verify_locations(str(ca))

		try:
			obj.session.parent.clients[obj.session.fileno].socket = ssl_context.wrap_socket(
				obj.session.parent.clients[obj.session.fileno].socket,
				server_side=True,
				do_handshake_on_connect=True,
				suppress_ragged_eofs=True
			)
			obj.session.parent.clients[obj.session.fileno].buffert = b''
			obj.session.parent.clients[obj.session.fileno].set_protection(True)
			obj.session.parent.configuration.storage.set_transaction_as_secure(obj.session.mail.transaction_id)
			# obj.session.parent.clients[obj.session.fileno].socket.send(bytes(f"220 {obj.session.parent.configuration.realms[0].fqdn} ESMTP\r\n", "UTF-8"))
		except ssl.SSLError:
			obj.session.set_parser(
				Parser(
					expectations=[
						QUIT
					]
				)
			)
			return None
		except ConnectionResetError:
			log(f"Client(address={obj.session.address}) disconnected during handshake", level=logging.DEBUG)
			obj.session.set_parser(
				Parser(
					expectations=[
					]
				)
			)
			return None

		obj.session.set_parser(
			Parser(
				expectations=[
					EHLO,
					QUIT
				]
			)
		)

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in STARTTLS.respond(obj):
			yield result


class QUIT:
	@staticmethod
	def can_hanadle(obj :CMD_DATA) -> bool:
		return obj.data.lower().startswith('quit')

	@staticmethod
	def respond(obj :CMD_DATA) -> Iterator[bytes]:
		log(f"Processing: QUIT", level=logging.DEBUG, fg="cyan")
		yield b'221 OK\r\n'

	@staticmethod
	def handle(obj :CMD_DATA) -> Iterator[bytes]:
		for result in QUIT.respond(obj):
			yield result

		obj.session.close()