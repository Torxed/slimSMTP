def test_configuration():
	import slimSMTP

	configuration = slimSMTP.Configuration(
		port=25,
		address='',
		realms=[
			slimSMTP.Realm(name='test.domain')
		]
	)