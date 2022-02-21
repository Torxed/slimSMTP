def test_server():
	import slimSMTP

	configuration = slimSMTP.Configuration(
		port=9054,
		address='',
		realms=[
			slimSMTP.Realm(name='test.domain')
		],
		storage=slimSMTP.Memory()
	)

	server = slimSMTP.Server(configuration)

	import socket
	s = socket.socket()
	s.connect(('127.0.0.1', 9054))
	s.close()