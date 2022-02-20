from typing import Optional, List
from pydantic import BaseModel
from ..sockets import Server
from .spam import validate_email_address, get_mail_servers, ip_in_spf
from ..exceptions import InvalidSender, InvalidAddress

class Mail(BaseModel):
	session :Server
	client_fd :int
	sender :str = ''
	recipients :List[str] = []
	body :str = ''

	class Config:
		arbitrary_types_allowed = True

	def add_sender(self, who):
		validate_email_address(who, self.session.configuration)
		domain_of_sender = who[who.find('@')+1:].strip()

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

	def add_recipient(self, who):
		validate_email_address(who, self.session.configuration)

		self.recipients.append(who)

	def add_body(self, data, newline=True):
		self.body += f"{data}\r\n"
