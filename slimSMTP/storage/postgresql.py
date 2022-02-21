import pydantic
import psycopg2
import logging
from typing import Optional
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

class PostgreSQL(pydantic.BaseModel):
	database :str
	server :str
	port :int = 5432
	username :str = ''
	password :str = ''
	session :Optional[psycopg2.extensions.connection] = None

	def __init__(self, **data):
		super().__init__(**data)

		try:
			self.session = psycopg2.connect(f"dbname={self.database} host={self.server} port={self.port} user='{self.username}' password='{self.password}'")
		except psycopg2.OperationalError:
			connection = psycopg2.connect(f"dbname=postgres host={self.server} port={self.port} user='{self.username}'")
			connection.set_session(autocommit=True)
			connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT);

			with connection.cursor() as cursor:
				cursor.execute(f"CREATE DATABASE {self.database};")

			connection.close()

			self.session = psycopg2.connect(f"dbname={self.database} host={self.server} port={self.port} user='{self.username}' password='{self.password}'")
			self.session.set_session(autocommit=True)

		self.setup_default_tables()

		from ..logger import log
		log(f"PostgreSQL storage ready for usage.", level=logging.DEBUG, fg="green")

	class Config:
		arbitrary_types_allowed = True

	def setup_default_tables(self):
		with self.session.cursor() as cursor:
			cursor.execute(f"CREATE TABLE IF NOT EXISTS emails (id BIGSERIAL PRIMARY KEY, sender VARCHAR(320), recipient VARCHAR(320), data VARCHAR(10485760), secure BOOLEAN, stored TIMESTAMP WITH TIME ZONE DEFAULT now());")
			cursor.execute(f"CREATE TABLE IF NOT EXISTS transactions (id BIGSERIAL PRIMARY KEY, email BIGINT, ip INET, authenticated BOOLEAN, secure BOOLEAN, connected TIMESTAMP WITH TIME ZONE DEFAULT now());")
			self.session.commit()

	def begin_transaction(self, address):
		from ..logger import log

		with self.session.cursor() as cursor:
			cursor.execute(
				f"INSERT INTO transactions (ip, authenticated, secure) VALUES (%s, %s, %s) RETURNING id;",
				(address[0], False, False)
			)
			transaction_id = cursor.fetchone()[0]

			self.session.commit()

		log(f"Gave {address} a transactional ID of: {transaction_id}", level=logging.DEBUG, fg="cyan")
		return transaction_id

	def set_transaction_as_secure(self, transaction_id):
		from ..logger import log

		log(f"Marking transaction {transaction_id} as secure (TLS Enabled)", level=logging.DEBUG, fg="green")

		with self.session.cursor() as cursor:
			cursor.execute(
				f"UPDATE transactions SET secure=true WHERE id=%s;",
				(transaction_id, )
			)

	def store_email(self, client):
		from ..logger import log

		log(f"Storing email from Client(address={client.address}, identity={client.mail.sender}, recipients={client.mail.recipients})", level=logging.INFO, fg="green")
		with self.session.cursor() as cursor:
			for recipient in client.mail.recipients:
				cursor.execute(
					f"INSERT INTO emails (sender, recipient, data, secure) VALUES (%s, %s, %s, %s) RETURNING id;",
					(client.mail.sender, recipient, client.mail.body, client.tls_protection is True)
				)
				id_of_new_row = cursor.fetchone()[0]

				cursor.execute(
					f"UPDATE transactions SET email=%s WHERE id=%s;",
					(client.mail.transaction_id, id_of_new_row)
				)
			
			self.session.commit()

		return True