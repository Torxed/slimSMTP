import pydantic
from typing import Callable

class Session(pydantic.BaseModel):
	addr: str
	port: int
	authenticated: bool = False
