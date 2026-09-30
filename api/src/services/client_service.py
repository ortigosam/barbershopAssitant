
from typing import Optional, Tuple, Any

from src.domain.exceptions import ClientAlreadyExistsError
from src.repositories.client_repository import ClientRepository
from src.schemas.client import ClientResponse


class ClientService:

    def __init__(self, repository: ClientRepository):
        self.repository = repository

    def _row_to_response(self, row: Tuple[Any, Any]) -> ClientResponse:
        return ClientResponse(telephone=row[0], name=row[1])

    def get_client(self, telephone: str) -> Optional[ClientResponse]:
        row = self.repository.get_by_telephone(telephone)

        if row is None:
            return None

        return self._row_to_response(row)

    def create_client(self, telephone: str, name: str) -> ClientResponse:
        existing_client = self.repository.get_by_telephone(telephone)

        if existing_client is not None:
            raise ClientAlreadyExistsError(f"Client {telephone} already exists")

        row = self.repository.create(telephone=telephone, name=name)
        return self._row_to_response(row)