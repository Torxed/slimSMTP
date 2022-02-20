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

while server.poll() is True:
	for client in server:
		if data := client.get_data():
			for response in client.parse(data):
				client.respond(response)

	for client in server.process_idle_connections():
		pass