def test_parser():
	import socket
	import slimSMTP

	configuration = slimSMTP.Configuration(
		port=9052,
		address='',
		realms=[
			slimSMTP.Realm(name='hvornum.se')
		]
	)

	parser = slimSMTP.Parser(
		expectations=[
			slimSMTP.EHLO,
			slimSMTP.QUIT
		]
	)

	server = slimSMTP.Server(configuration)
	client = slimSMTP.Client(
		parent=server,
		socket=socket.socket(),
		fileno=1,
		address=('127.0.0.1', 8950),
		parser=parser,
		mail=slimSMTP.Mail(
			session=server,
			client_fd=-1,
			transaction_id=-1
		)
	)
	server.clients[1] = client

	for response in parser.parse(
			slimSMTP.CMD_DATA(
				data=b'EHLO <domain>\r\n',
				realms=configuration.realms,
				session=client
			)
		):

		pass