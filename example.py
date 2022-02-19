import slimSMTP

configuration = slimSMTP.Configuration(
	port=25,
	bind='',
	realms=[
		slimSMTP.Realm(name='hvornum.se')
	]
)

# listener = slimSMTP.serve(configuration)
session = slimSMTP.Session(addr='127.0.0.1', port=81923, authenticated=True)

parser = slimSMTP.Parser(
	expectations=[
		slimSMTP.EHLO,
		slimSMTP.QUIT
	]
)

for response in parser.parse(
	slimSMTP.CMD_DATA(
		data=b'EHLO <domain>\r\n',
		realm=configuration.realms[0],
		session=session
	)):

	print('Respnding with:', response)

b'220 mail-halon-02.fbg1.glesys.net ESMTP\r\n'
b'EHLO <domain>\r\n'
b'250-mail-halon-02.fbg1.glesys.net\r\n250-PIPELINING\r\n250-SIZE 61440000\r\n250-STARTTLS\r\n250-AUTH LOGIN PLAIN\r\n250-ENHANCEDSTATUSCODES\r\n250 8BITMIME\r\n'
b'QUIT\r\n'
b'221 2.0.0 Bye\r\n'