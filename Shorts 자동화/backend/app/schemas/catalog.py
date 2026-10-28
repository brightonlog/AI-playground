from pydantic import BaseModel


class Template(BaseModel):
    id: str
    name: str
    description: str
    available: bool
