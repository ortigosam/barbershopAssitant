from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Path

from src.api.dependencies import ClientServiceDep
from src.domain.exceptions import ClientAlreadyExistsError
from src.schemas.client import ClientCreate, ClientResponse


router = APIRouter(
    prefix="/clients",
    tags=["clients"],
)


@router.get(
    "/{telephone}",
    response_model=ClientResponse,
)
def get_client(
    telephone: Annotated[str, Path(min_length=1)],
    service: ClientServiceDep,
) -> ClientResponse:
    client = service.get_client(telephone)

    if client is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found",
        )

    return client


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_client(
    client: ClientCreate,
    service: ClientServiceDep,
) -> ClientResponse:
    try:
        result = service.create_client(
            telephone=client.telephone,
            name=client.name,
        )

    except ClientAlreadyExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return result