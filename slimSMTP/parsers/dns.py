import re
import shlex
import ipaddress
import dns.resolver
from typing import List
from ..exceptions import SPFError

class SPF:
	def __init__(self, initial_data :str):
		if not (version_data := re.findall('v=spf[0-9]+', initial_data)):
			raise SPFError(f"Not a SPF record: {initial_data}")

		initial_data = initial_data.replace('" "', ' ')
		
		self.version = version_data[0]
		self.hosts :List[str] = []

		for field in shlex.split(initial_data.strip('"')):
			if ':' in field:
				key, value = field.split(':', 1)
			elif '=' in field:
				key, value = field.split('=', 1)

			if key == 'include':
				for record in dns.resolver.resolve(value, 'TXT', search=True):
					try:
						for host in SPF(record.to_text()).hosts:
							self.hosts.append(host)
					except SPFError:
						pass
			elif key == 'redirect':
				for record in dns.resolver.resolve(value, 'TXT', search=True):
					try:
						for host in SPF(record.to_text()).hosts:
							self.hosts.append(host)
					except SPFError:
						pass
			elif key == 'ip4':
				if '/' not in value:
					value += '/32'

				self.hosts.append(ipaddress.ip_network(value, False))
			elif key == 'a':
				# Authorize (https://support.google.com/a/answer/10683907?hl=en)
				try:
					ip = value
					if not '/' in ip:
						ip += '/32'
					self.hosts.append(ipaddress.ip_network(ip))
				except ValueError:
					try:
						for record in dns.resolver.resolve(value, 'A', search=True):
							self.hosts.append(ipaddress.ip_network(f"{record.to_text()}/32"))
					except dns.resolver.NoAnswer:
						pass