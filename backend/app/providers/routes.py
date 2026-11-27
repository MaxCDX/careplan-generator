from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.providers.schemas import ProviderCreate, ProviderCreated
from app.providers.service import create_provider

router = APIRouter(prefix="/providers", tags=["providers"])


@router.post("", response_model=ProviderCreated, status_code=201, responses={
    400: {"description": "Invalid provider input"},
    409: {"description": "Duplicate NPI or provider name requiring confirmation"},
})
def register_provider(data: ProviderCreate, db: Session = Depends(get_db)):
    provider = create_provider(db, data)
    return ProviderCreated(id=provider.id, name=provider.name, npi=provider.npi, created_at=provider.created_at)
