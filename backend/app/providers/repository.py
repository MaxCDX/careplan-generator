from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.providers.models import Provider


def get_provider_by_npi(db: Session, npi: str) -> Provider | None:
    """Return an existing Provider by NPI."""
    return db.query(Provider).filter(Provider.npi == npi).one_or_none()


def get_provider_by_name(db: Session, name: str) -> Provider | None:
    return (
        db.query(Provider)
        .filter(func.lower(Provider.name) == func.lower(name))
        .order_by(Provider.id)
        .first()
    )


def insert_provider(db: Session, *, name: str, npi: str) -> Provider:
    provider = Provider(name=name, npi=npi)
    db.add(provider)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise
    db.refresh(provider)
    return provider


def get_or_create_provider(db: Session, *, name: str, npi: str) -> Provider:
    """Return an existing Provider by NPI or create one for this workflow."""
    provider = get_provider_by_npi(db, npi)
    if provider:
        return provider

    provider = Provider(name=name, npi=npi)
    db.add(provider)
    db.flush()
    return provider
