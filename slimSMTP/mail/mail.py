import logging
from typing import List
from pydantic import BaseModel
from .spam import validate_email_address, get_mail_servers, ip_in_spf, spammer
from ..sockets import Server
from ..exceptions import InvalidSender, AuthenticationError
from ..logger import log

class Mail(BaseModel):
	session :Server
	client_fd :int
	transaction_id :int
	sender :str = ''
	recipients :List[str] = []
	body :str = ''

	class Config:
		arbitrary_types_allowed = True

	def add_sender(self, who :str) -> None:
		validate_email_address(who, self.session.configuration)
		domain_of_sender = who[who.find('@') + 1:].strip()

		allowed_sender = True
		for realm in self.session.configuration.realms:
			if realm.name == domain_of_sender:
				allowed_sender = False
				break

		if not allowed_sender:
			raise InvalidSender(f"Client is not allowed to send on behalf of internal realm {domain_of_sender}")

		if (spf := ip_in_spf(self.session.clients[self.client_fd].address[0], domain_of_sender)) is False:
			raise InvalidSender(f"Client is not allowed to send e-mails from {domain_of_sender} on IP {self.session.clients[self.client_fd].address[0]} due to SPF records")
		
		elif spf is None:
			allowed_sender = False
			for ip in get_mail_servers(domain_of_sender):
				if ip == self.session.clients[self.client_fd].address[0]:
					allowed_sender = True
					break

			if not allowed_sender:
				raise InvalidSender(f"Client is not allowed to send e-mails from {domain_of_sender} on IP {self.session.clients[self.client_fd].address[0]} due to MX records")

		self.sender = who

	def add_recipient(self, who :str) -> None:
		# b'MAIL FROM:<anton.doxid@gmail.com> SIZE=2104\r\n'
		# b'RCPT TO:<anton@archlinux.life>\r\n'
		validate_email_address(who, self.session.configuration)

		domain_of_recipient = who[who.find('@') + 1:].strip()

		internal_domain = False
		for realm in self.session.configuration.realms:
			if realm.name == domain_of_recipient:
				internal_domain = True
				break

		if not internal_domain and self.session.clients[self.client_fd].authenticated is False:
			log_message = f"Client({self.session.clients[self.client_fd]}) attempted to send externally without authentication."
			
			log(log_message, level=logging.WARNING, fg="red")
			
			# If the client tried to send externally, without authentication (which we don't support yet)
			# then it's definetely a spammer.
			spammer(self.session.clients[self.client_fd])
			self.session.clients[self.client_fd].close()
			
			raise AuthenticationError(log_message)

		self.recipients.append(who)

	def add_body(self, data :str, newline :bool = True) -> None:
		self.body += f"{data}\r\n"
