import psycopg2
from os.path import expanduser, abspath
from time import time
# import splitMail - Is auto-loaded from slim_smtp.py __builtins__

class postgresql():
	def __init__(self):
		core['storages']['@POSTGRESQL'] = self
		list(pg_query("CREATE TABLE IF NOT EXISTS postgresql_mailboxes (id SERIAL PRIMARY KEY, mailbox VARCHAR(255), domain VARCHAR(255), UNIQUE(mailbox, domain));"))
		list(pg_query("CREATE TABLE IF NOT EXISTS postgresql_mailroom (id BIGSERIAL PRIMARY KEY, mailbox_id VARCHAR(255), mail VARCHAR(8192), registered TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now());"))
		# mailbox, domain,  account_backend
		# anton    gh.com   MATRIX
		# anton    @SOCIAL  ALIAS
		# jb       gh.com   PAM
		# facebook gh.com   @SOCIAL
		# twitter  gh       @SOCIAL

	def getDomains(self):
		results = []
		for row in pg_query("SELECT domain FROM smtp;"):
			if row['domain'] in results: continue
			
			results.append(row['domain'])

		return results

	def store(self, _from, _to, message):
		mailbox, domain = splitMail(_to)

		for row in pg_query("SELECT * FROM smtp WHERE mailbox='"+mailbox+"' AND domain='"+domain+"';"):

			delivered = False
			for subrow in pg_query("SELECT * FROM postgresql_mailboxes WHERE mailbox='"+mailbox+"' AND domain='"+domain+"';"):
				if subrow is None: break
				log(' | Delivering to database storage:', subrow['id'])
				list(pg_query("INSERT INTO postgresql_mailroom (mailbox_id, mail) VALUES("+str(subrow['id'])+", '"+message+"')"))
				delivered = True
			if delivered: return delivered

			## Backup, deliver to PAM (TODO: make PAM plugin):
			if row['account_backend'] == 'POSTGRESQL':
				log(' | Delivering to local storage: ~/'+row['mailbox'], '(postgresql)')

				mail_file = abspath('{home_dir}/Maildir/new/{from}-{time}.mail'.format(**{'home_dir' : expanduser('~'+row['mailbox']),
																						  'from' : _from,
																						  'time' : time()}))
				save_mail(mail_file, message, row['mailbox'])
				return True

			elif row['account_backend'][0] == '@':
				# TODO: Don't forget to check backend_account against subcursor results!
				#       :)
				log(' | Delivering to shared mailbox:', row['mailbox'], '(postgresql)')
				log(' |- Members:')

				for subrow in pg_query("SELECT * FROM smtp WHERE domain='"+row['account_backend']+"';"): #subcur.fetchall():
					log(' |    ', subrow['mailbox']+'@'+row['domain'])
					mail_file = abspath('{home_dir}/Maildir/new/{from}-{time}.mail'.format(**{'home_dir' : expanduser('~'+subrow['mailbox']),
																						  'from' : _from,
																						  'time' : time()}))
					save_mail(mail_file, message, subrow['mailbox'])
				return True

postgresql()