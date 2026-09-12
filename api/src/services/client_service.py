
from src.domain.exceptions import (
    ClientAlreadyExistsError,
)
from src.repositories.client_repository import ClientRepository
from src.schemas.client import ClientResponse


class ClientService:

    def __init__(self, repository: ClientRepository):
        self.repository = repository

    def get_client(self, telephone: str):
        row = self.repository.get_by_telephone(telephone)

        if row is None:
            return None

        return ClientResponse(telephone=row[0], name=row[1])

    def create_client(self, telephone: str, name: str):
        existing_client = self.repository.get_by_telephone(telephone)

        if existing_client is not None:
            raise ClientAlreadyExistsError(
                f"Client {telephone} already exists"
            )

        row = self.repository.create(
            telephone=telephone,
            name=name,
        )

        return ClientResponse(telephone=row[0], name=row[1])