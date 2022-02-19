import pydantic
from typing import List
from ..realms import Realm

class Configuration(pydantic.BaseModel):
	port: int
	address: str
	realms: List[Realm]