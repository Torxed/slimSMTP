import pydantic

class Realm(pydantic.BaseModel):
	name: str

	@property
	def fqdn(self) -> str:
		return self.name
	