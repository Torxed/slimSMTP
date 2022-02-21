import ssl
import dns.resolver
import logging
import smtplib
# from email import encoders
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText
# from email.mime.base import MIMEBase
from typing import Dict, Any
from .spam import validate_email_address
from ..logger import log

def deliver_external_email(session, sender, reciever, data, secure = False):
	validate_email_address(reciever, session.configuration)
	domain_of_reciever = reciever[reciever.find('@') + 1:].strip()

	# email = MIMEMultipart('alternative')
	# email['Subject'] = configuration['SUBJECT']
	# email['From'] = "SSH Guard <{SSH_MAIL_USER_FROM}@{DOMAIN}>".format(**configuration)
	# email['To'] = "{SSH_MAIL_TO_REALNAME} <{SSH_MAIL_USER_TO}@{SSH_MAIL_USER_TODOMAIN}>".format(**configuration)
	# email['Message-ID'] = configuration['Message-ID']
	# email.preamble = configuration['SUBJECT']

	# text = load_text_template()
	# html = load_html_template()


	# email_body_text = MIMEText(text, 'plain')
	# email_body_html = MIMEBase('text', 'html')
	# email_body_html.set_payload(html)
	# encoders.encode_quopri(email_body_html)
	# email_body_html.set_charset('UTF-8')

	# email.attach(email_body_text)
	# email.attach(email_body_html)

	# email["DKIM-Signature"] = sign_email(email)

	context = ssl.create_default_context()
	for mx_record in dns.resolver.query(domain_of_reciever, 'MX'):
		mail_server = mx_record.to_text().split()[1][:-1]
		log(f"Attempting to deliver external email using {mail_server}", level=logging.DEBUG, fg="cyan")
		try:
			server = smtplib.SMTP(mail_server, port=25, timeout=10) # 587 = TLS, 465 = SSL
			if server.starttls(context=context)[0] != 220:
				log('Could not start TLS.', level=logging.ERROR, fg="red")
				server.quit()
				continue
			
			server.sendmail(sender, reciever, data)
			server.quit()

			return True
		except Exception as e:
			log(f"Could not send email via {mail_server}: {e}", level=logging.ERROR, fg="red")

	return False