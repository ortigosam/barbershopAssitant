from pydantic import BaseModel


class ClientCreate(BaseModel):
    telephone: str
    name: str


class ClientResponse(BaseModel):
    telephone: str
    name: str