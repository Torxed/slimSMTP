import pydantic

class Session(pydantic.BaseModel):
	addr: str
	port: int
	authenticated: bool = False
