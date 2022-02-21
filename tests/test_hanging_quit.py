def test_hanging_quit():
	import time
	import slimSMTP

	configuration = slimSMTP.Configuration(
		port=9051,
		address='',
		realms=[
			slimSMTP.Realm(name='test.domain')
		],
		hanging_timeouts=2.0
	)

	hosts_lines = []
	found_test = False
	found_internal = False
	with open('/etc/hosts', 'r') as fh:
		for line in fh:
			hosts_lines.append(line)

			if 'test.domain' in line and '127.0.0.1' in line:
				found_test = True

			if 'internal.domain' in line and '127.0.0.1' in line:
				found_internal = True

	if not found_test:
		with open('/etc/hosts', 'a') as fh:
			fh.write("127.0.0.1\ttest.domain\n")
	if not found_internal:
		with open('/etc/hosts', 'a') as fh:
			fh.write("127.0.0.1\tinternal.domain\n")

	server = slimSMTP.Server(configuration)

	from threading import Thread
	class sender_thread(Thread):
		def __init__(self):
			super(sender_thread, self).__init__()
			self.start()

		def run(self):
			import socket
			s = socket.socket()
			s.connect(('127.0.0.1', 9051))
			
			if not b'220' in s.recv(8192):
				exit(1)

			s.send(b'EHLO testing.domain\r\n')
			if not b'250-' in s.recv(8192):
				exit(1)

			s.send(b'mail from: testsson@internal.domain\r\n')
			if not b'250' in s.recv(8192):
				exit(1)

			s.send(b'rcpt to: testsson@test.domain\r\n')
			if not b'250' in s.recv(8192):
				exit(1)

			s.send(b'data\r\n')
			if not b'354' in s.recv(8192):
				exit(1)

			s.send(b'test!\r\n')
			s.send(b'\r\n.\r\n')
			if not b'250' in s.recv(8192):
				exit(1)

			s.recv(8192)
			# s.send(b'QUIT\r\n')
			# if not b'221' in s.recv(8192):
			# 	exit(1)

			s.close()

	sender = sender_thread()

	alive = True
	while server.poll() is True and alive:
		for client in server:
			if data := client.get_data():
				for response in client.parse(data):
					client.respond(response)

		for client in server.process_idle_connections():
			alive = False
			break

	server.close()

	if found_test is False or found_internal is False:
		with open('/etc/hosts', 'w') as fh:
			for line in hosts_lines:
				fh.write(line)