import socket
import slimSMTP

configuration = slimSMTP.Configuration(
	port=25,
	address='',
	realms=[
		slimSMTP.Realm(name='hvornum.se')
	]
)

server = slimSMTP.Server(configuration)

# # listener = slimSMTP.serve(configuration)
# session = slimSMTP.Client(parent=server, socket=socket.socket(), address=('127.0.0.1', 8950))

# parser = slimSMTP.Parser(
# 	expectations=[
# 		slimSMTP.EHLO,
# 		slimSMTP.QUIT
# 	]
# )

# for response in parser.parse(
# 	slimSMTP.CMD_DATA(
# 		data=b'EHLO <domain>\r\n',
# 		realms=configuration.realms,
# 		session=session
# 	)):

# 	print('Respnding with:', response)

while server.poll() is True:
	for client in server:
		if data := client.get_data():
			for response in client.parse(data):
				client.respond(response)


b'220 mail-halon-02.fbg1.glesys.net ESMTP\r\n'
b'EHLO <domain>\r\n'
b'250-mail-halon-02.fbg1.glesys.net\r\n250-PIPELINING\r\n250-SIZE 61440000\r\n250-STARTTLS\r\n250-AUTH LOGIN PLAIN\r\n250-ENHANCEDSTATUSCODES\r\n250 8BITMIME\r\n'
b'QUIT\r\n'
b'221 2.0.0 Bye\r\n'