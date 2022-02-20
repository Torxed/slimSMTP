from typing import Optional, List
from pydantic import BaseModel
from ..sockets import Client
from .spam import validate_email_address, get_mail_servers
from ..exceptions import InvalidSender, InvalidAddress

class Mail(BaseModel):
	session :Client
	sender :str = ''
	recipients :List[str] = []
	body :str = ''

	def add_sender(self, who):
		validate_email_address(who, self.session.parent.configuration)
		domain_of_sender = who[who.find('@')+1:].strip()

		allowed_sender = True
		for realm in self.session.parent.configuration.realms:
			if realm.name == domain_of_sender:
				allowed_sender = False
				break

		if not allowed_sender:
			raise InvalidSender(f"Client is not allowed to send on behalf of internal realm {domain_of_sender}")

		allowed_sender = False
		for ip in get_mail_servers(domain_of_sender):
			if ip == self.session.address[0]:
				allowed_sender = True
				break

		if not allowed_sender:
			raise InvalidSender(f"Client is not allowed to send e-mails from {domain_of_sender} on IP {self.session.address[0]} due to MX records")

		self.sender = who

	def add_recipient(self, who):
		validate_email_address(who, self.session.parent.configuration)

		self.recipients.append(who)

	def add_body(self, data, newline=True):
		self.body += f"{data}\r\n"
