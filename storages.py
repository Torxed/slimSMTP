from os import makedirs
from os.path import isfile, isdir, abspath, expanduser, basename
from helpers import generate_UID

class maildir():
	def __init__(self, path='~/Maildir'):
		self.path = abspath(expanduser(path))
		if not isdir(self.path):
			makedirs(self.path)

	def store(self, sender, reciever, message):
		destination = '{}/{}.mail'.format(self.path, generate_UID())
		log('Stored mail from {} to reciever {} under \'{}\''.format(sender, reciever, destination), product='slimSMTP', handler='storage_maildir', level=3)
		with open(destination, 'wb') as mail:
			mail.write(message)

		return True
