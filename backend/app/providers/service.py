from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import ConflictError
from app.providers import repository
from app.providers.models import Provider
from app.providers.schemas import ProviderCreate


def npi_conflict(provider: Provider) -> ConflictError:
    return ConflictError(
        code="PROVIDER_NPI_CONFLICT",
        message="A provider with this NPI already exists.",
        detail={"existing_provider_id": provider.id},
    )


def create_provider(db: Session, data: ProviderCreate) -> Provider:
    existing = repository.get_provider_by_npi(db, data.npi)
    if existing:
        raise npi_conflict(existing)

    if not data.confirm:
        match = repository.get_provider_by_name(db, data.name)
        if match:
            raise ConflictError(
                code="PROVIDER_POSSIBLE_DUPLICATE",
                message="A provider with this name already exists. Verify the NPI before confirming.",
                detail={"existing_provider_id": match.id, "existing_npi": match.npi},
            )

    try:
        return repository.insert_provider(db, name=data.name, npi=data.npi)
    except IntegrityError:
        # Another request may have registered this unique NPI after the lookup.
        existing = repository.get_provider_by_npi(db, data.npi)
        if existing:
            raise npi_conflict(existing)
        raise
