def test_server():
	import slimSMTP

	configuration = slimSMTP.Configuration(
		port=9049,
		address='',
		realms=[
			slimSMTP.Realm(name='test.domain')
		]
	)

	server = slimSMTP.Server(configuration)

	import socket
	s = socket.socket()
	s.connect(('127.0.0.1', 9049))
	s.close()