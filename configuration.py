from ssl import PROTOCOL_TLSv1
from storages import maildir

config = {'pidfile' : '/var/run/slimSMTP.pid',
		  
		  'DOMAINS' : {'xn--frvirrad-n4a.se' : {}, 'hvornum.se' : {}},
		  'log_level' : 2,
		  'log' : True,
		  'resolve' : False,
		  
		  'ssl' : {'enabled' : True,
		  			'forced' : True,
					 'key' : '/etc/letsencrypt/live/hvornum.se/privkey.pem',
					 'cert' : '/etc/letsencrypt/live/hvornum.se/cert.pem',
					 'VERSION' : PROTOCOL_TLSv1},

		  'login_methods' : ['pam', 'postgresql', 'internal'],

		  'users' : {'anton' : {'password' : 'test', 'storage' : maildir('/home/anton/Maildir/new')} },
		  'mailboxes' : {'anton@hvornum.se' : 'anton',
		  				 'anton@xn--frvirrad-n4a.se' : 'anton',
						 '*@hvornum.se' : 'anton'}, # This defaults all unknown @hvornum.se recipiants to 'anton'

		  'postgresql' : {'database' : 'slimSMTP', 'username' : 'slimSMTP', 'password' : 'test'},
		  'poll_timeout' : 0.5
		}
