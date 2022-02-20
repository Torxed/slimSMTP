def test_cmd_data():
	import socket
	import slimSMTP

	configuration = slimSMTP.Configuration(
		port=9051,
		address='',
		realms=[
			slimSMTP.Realm(name='hvornum.se')
		]
	)

	server = slimSMTP.Server(configuration)
	session = slimSMTP.Client(parent=server, socket=socket.socket(), address=('127.0.0.1', 8950))

	slimSMTP.CMD_DATA(
		data=b'EHLO <domain>\r\n',
		realms=configuration.realms,
		session=session
	)