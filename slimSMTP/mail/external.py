import ssl
import dns.resolver
import logging
import smtplib
import email
import dkim
# from email import encoders
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
from typing import Dict, Any
from .spam import validate_email_address
from ..logger import log

# https://russell.ballestrini.net/quickstart-to-dkim-sign-email-with-python/
def sign_email(mail_obj, session, selector='default', domain=None):
	if type(selector) != bytes: selector = bytes(selector, 'UTF-8')
	if type(domain) != bytes: domain = bytes(domain, 'UTF-8')

	if not session.configuration.DKIM_KEY.exists():
		log(f"Missing DKIM key: {session.configuration.DKIM_KEY}", level=logging.ERROR, fg="red")
		return False

	with session.configuration.DKIM_KEY.open('rb') as fh:
		dkim_private_key_data = fh.read()

	sig = dkim.sign(message=bytes(mail_obj.as_string(), 'UTF-8'),
					selector=selector,
					domain=domain,
					privkey=dkim_private_key_data,
					include_headers=["To", "From", "Subject"])

	return sig.lstrip(b"DKIM-Signature: ").decode('UTF-8')

def deliver_external_email(session, sender, reciever, data, secure = False):
	validate_email_address(sender, session.configuration)
	validate_email_address(reciever, session.configuration)
	domain_of_sender = sender[sender.find('@') + 1:].strip()
	domain_of_reciever = reciever[reciever.find('@') + 1:].strip()

	if session.configuration.DKIM_KEY:
		mail_obj = email.message_from_string(data)
		if not (signature := sign_email(mail_obj, session=session, domain=domain_of_sender)):
			return False

		mail_obj["DKIM-Signature"] = signature

	context = ssl.create_default_context()
	for mx_record in dns.resolver.query(domain_of_reciever, 'MX'):
		mail_server = mx_record.to_text().split()[1][:-1]
		log(f"Attempting to deliver external email from {sender} to {reciever} using {mail_server}", level=logging.DEBUG, fg="cyan")
		try:
			server = smtplib.SMTP(mail_server, port=25, timeout=10) # 587 = TLS, 465 = SSL
			if server.starttls(context=context)[0] != 220:
				log('Could not start TLS.', level=logging.ERROR, fg="red")
				server.quit()
				continue
			
			server.sendmail(sender, reciever, mail_obj.as_string())
			server.quit()

			return True
		except Exception as e:
			log(f"Could not send email via {mail_server}: {e}", level=logging.ERROR, fg="red")

	return False