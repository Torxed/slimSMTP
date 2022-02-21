import logging
import datetime
from typing import List, Optional
from pydantic import BaseModel
from .spam import validate_email_address, get_mail_servers, ip_in_spf, spammer
from ..sockets import Server
from ..exceptions import InvalidSender, AuthenticationError
from ..logger import log

class ExternalEmail(BaseModel):
	email_id :int
	session :Server
	sender: str
	recipient: str
	data :str
	secure :bool
	stored :datetime.datetime
	delivery_attempts :int
	delivered: Optional[datetime.datetime] = None
	last_delivery_attempt :Optional[datetime.datetime] = None

	class Config:
		arbitrary_types_allowed = True

	def __init__(self, **data):
		data['email_id'] = data['id']
		super().__init__(**data)

	def deliver(self):
		from .external import deliver_external_email

		if self.last_delivery_attempt:
			delta = datetime.datetime.now(self.last_delivery_attempt.tzinfo) - self.last_delivery_attempt
			seconds_in_day = 24 * 60 * 60
			minutes, seconds = divmod(delta.days * seconds_in_day + delta.seconds, 60)

			time_delta_since_last_attempt_in_minutes = (minutes * 60 + seconds) / 60

			if time_delta_since_last_attempt_in_minutes < 1:
				return False

		if deliver_external_email(self.session, self.sender, self.recipient, self.data, self.secure):
			self.session.configuration.storage.set_as_delivered(self.email_id)

			return True
		else:
			self.session.configuration.storage.update_delivery_attempt(self.email_id)

		return False


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

		internal_domain = False
		for realm in self.session.configuration.realms:
			if realm.name == domain_of_sender:
				internal_domain = True
				break

		if internal_domain and self.session.clients[self.client_fd].authenticated is not True:
			raise AuthenticationError(f"Client is not allowed to send on behalf of internal realm {domain_of_sender}")

		if internal_domain is False:
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
			self.session.clients[self.client_fd].spammer(log_message)
			self.session.clients[self.client_fd].close()
			
			raise AuthenticationError(log_message)

		self.recipients.append(who)

	def add_body(self, data :str, newline :bool = True) -> None:
		self.body += f"{data}\r\n"
