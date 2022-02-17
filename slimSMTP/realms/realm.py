import pydantic

class Realm(pydantic.BaseModel):
	name: str

	@property
	def fqdn(self):
		return self.name
	