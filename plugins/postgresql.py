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
		# anton    gh.com   POSTGRESQL
		# anton    @SOCIAL  ALIAS
		# facebook gh.com   @SOCIAL
		# twitter  gh       @SOCIAL

	def getDomains(self):
		"""
		getDomains() is called in order to ask the plugin what domains it host.
		This makes slim_smtp easier to expand since it only handles on domain today.
		"""
		results = []
		for row in pg_query("SELECT domain FROM smtp;"):
			if row['domain'] in results: continue
			
			results.append(row['domain'])

		return results

	def store(self, _from, _to, message):
		"""
		splitMail() is a global function inherited from slim_smtp by default.
		save_mail() is also globally inherited, in case you need to save mails to disk.
		"""
		mailbox, domain = splitMail(_to)

		delivered = False
		for subrow in pg_query("SELECT * FROM postgresql_mailboxes WHERE mailbox='"+mailbox+"' AND domain='"+domain+"';"):
			if subrow is None: break
			log(' | Delivering to database storage:', subrow['id'])
			list(pg_query("INSERT INTO postgresql_mailroom (mailbox_id, mail) VALUES("+str(subrow['id'])+", '"+message+"')"))
			delivered = True
		if delivered: return delivered

postgresql()
