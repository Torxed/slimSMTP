import pathlib
import dns.resolver
import time
import logging
import socket
import ipaddress
from ..logger import log
from ..exceptions import SPFError
from ..parsers.dns import SPF

def validate_top_level_domain(domain, configuration):
	if domain[:1] == '.':
		domain = domain[1:]

	if domain not in configuration.valid_top_domains:
		raise InvalidAddress(f"TLD of recipient not a valid TLD: {domain}")

def validate_email_address(addr, configuration):
	if (at_char := addr[:64].find('@')) <= 0:
		raise InvalidAddress(f"Local part in address is to long.")

	if len(addr[at_char:at_char+257]) > 255:
		raise InvalidAddress(f"Domain name in address is to long.")

	# Redudant, but shows in a more simplistic term what our limits are.
	if len(addr[:321]) > 320:
		raise InvalidAddress(f"Address is to long in general.")

	# Allowed top domains is taking from the Mozilla PSL:
	# https://github.com/publicsuffix/list/blob/master/public_suffix_list.dat
	# Extract TLD: cat public_suffix_list.dat | grep -Ev '^#|^/' | awk -F[.:] '{print $NF}' | sort | uniq

	validate_top_level_domain(pathlib.PurePath(addr).suffix, configuration)

def get_mail_servers(domain):
	log(f"Getting IP for all MX records on domain {domain}", level=logging.DEBUG)
	try:
		for mx_record in dns.resolver.resolve(domain, 'MX', search=True):
			mail_server = mx_record.exchange.to_text()
			log(f"Found mail server: {mail_server}", level=logging.DEBUG)
			for ip_record in dns.resolver.resolve(mail_server, 'A', search=True):
				log(f"Resolved mail server to IP: {ip_record.to_text()}", level=logging.DEBUG)
				yield ip_record.to_text()
	except dns.resolver.NXDOMAIN:
		ip_record = socket.gethostbyname(domain)
		log(f"Found IP using simple forward DNS lookup using socket library: {ip_record}", level=logging.DEBUG)
		yield ip_record

def ip_in_spf(ip, domain):
	found_spf = False
	for record in dns.resolver.resolve(domain, 'TXT', search=True):
		try:
			for subnet in SPF(record.to_text()).hosts:
				found_spf = True
				if ipaddress.ip_address(ip) in subnet:
					return True
		except SPFError:
			pass

	if found_spf:
		return False
	else:
		return None

spam_assasin = {}
def spammer(client):
	spam_assasin[client.address[0]] = time.time()

def is_spammer(ip):
	if ip in spam_assasin:
		return True

	return False
