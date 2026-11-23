from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.patients.schemas import PatientCreate, PatientCreated
from app.patients.service import create_patient
from app.patients.serializers import serialize_created_patient

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientCreated, status_code=201,
             responses={400: {"description": "Invalid input"}, 409: {"description": "Duplicate patient"}})
def register_patient(data: PatientCreate, db: Session = Depends(get_db)):
    return serialize_created_patient(create_patient(db, data))
