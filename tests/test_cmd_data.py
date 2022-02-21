def test_cmd_data():
	import socket
	import slimSMTP

	configuration = slimSMTP.Configuration(
		port=9050,
		address='',
		realms=[
			slimSMTP.Realm(name='hvornum.se')
		]
	)

	server = slimSMTP.Server(configuration)
	session = slimSMTP.Client(
		parent=server,
		socket=socket.socket(),
		fileno=1,
		address=('127.0.0.1', 8950),
		parser=slimSMTP.Parser(
			expectations=[
				slimSMTP.QUIT
			]
		),
		mail=slimSMTP.Mail(
			session=server,
			client_fd=-1,
			transaction_id=-1
		)
	)

	slimSMTP.CMD_DATA(
		data=b'EHLO <domain>\r\n',
		realms=configuration.realms,
		session=session
	)