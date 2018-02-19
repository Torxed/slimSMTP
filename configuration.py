from ssl import PROTOCOL_TLSv1

try:
	from storages import maildir
except:
	## !!
	## == This is a static function NOT able to import via helpers.
	##    The main reason being helpers import configuration.py causing weird loops.
	##    And if not storages.py is in ./ we'll need to import via path (/usr/lib/slimSMTP/*)
	import imp, importlib.machinery
	from os.path import basename
	def custom_load(path, namespace=None):
		if not namespace: namespace = basename(path).replace('.py', '').replace('.', '_')

		loader = importlib.machinery.SourceFileLoader(namespace, path)
		handle = loader.load_module(namespace)
		return handle

	handle = custom_load('/usr/lib/slimSMTP/storages.py')
	maildir = handle.maildir

		  
config = {
		  'DOMAINS' : {'xn--frvirrad-n4a.se' : {}, 'hvornum.se' : {}},
		  'login_methods' : ['pam', 'postgresql', 'internal'],
		  
		  'users' : {'anton' : {'password' : 'test', 'storage' : maildir('/home/anthvo/Maildir/new', owner='anthvo')} },
		  'mailboxes' : {'anton@hvornum.se' : 'anton',
		  				 'anton@xn--frvirrad-n4a.se' : 'anton',
						 '*@hvornum.se' : 'anton'}, # This defaults all unknown @hvornum.se recipiants to 'anton'
						 
		  'ssl' : {'enabled' : True,
		  			'forced' : True,
					 'key' : '/etc/letsencrypt/live/hvornum.se/privkey.pem',
					 'cert' : '/etc/letsencrypt/live/hvornum.se/cert.pem',
					 'VERSION' : PROTOCOL_TLSv1},

		  ## Default file permissions, owner and group can be specified in maildir() initilization to override this:
		  'filepermissions' : {'owner' : 'root', 'group' : 'root', 'mod' : 0x0777},
		  'postgresql' : {'database' : 'slimSMTP', 'username' : 'slimSMTP', 'password' : 'test'},
		  'log_level' : 2,
		  'log' : True,
		  'resolve' : False,
		  'pidfile' : '/var/run/slimSMTP.pid',
		  'poll_timeout' : 0.5
		}
