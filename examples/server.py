import ssl
import slimSMTP

# openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -sha256 -days 365 -nodes

configuration = slimSMTP.Configuration(
	port=25,
	address='',
	realms=[
		slimSMTP.Realm(name='test.domain')
	],
	storage=slimSMTP.PostgreSQL(database='email', server='127.0.0.1', username='slimsmtp', password='i haz password'),
	tls_key='./key.pem',
	tls_cert='./cert.pem',
	tls_protocol=ssl.PROTOCOL_TLSv1_2,
	tls_certificate_authorities=['/home/username/self_signing_ca.pem']
)

server = slimSMTP.Server(configuration)

while server.poll() is True:
	for client in server:
		if data := client.get_data():
			for response in client.parse(data):
				client.respond(response)

	for client in server.process_idle_connections():
		pass