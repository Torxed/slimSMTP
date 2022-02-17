import pydantic
from typing import Callable
from ..realms import Realm

class Session(pydantic.BaseModel):
	addr: str
	port: int
