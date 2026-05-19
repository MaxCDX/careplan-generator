from sqlalchemy.orm import Session

from app.providers.models import Provider


def get_or_create_provider(db: Session, *, name: str, npi: str) -> Provider:
    """Return an existing Provider by NPI or create one for this workflow."""
    provider = db.query(Provider).filter(Provider.npi == npi).one_or_none()
    if provider:
        return provider

    provider = Provider(name=name, npi=npi)
    db.add(provider)
    db.flush()
    return provider
