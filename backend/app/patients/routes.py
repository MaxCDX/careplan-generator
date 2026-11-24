from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.patients import repository
from app.patients.schemas import PatientCreate, PatientCreated, PatientListResponse
from app.patients.service import create_patient
from app.patients.serializers import serialize_created_patient, serialize_patient_list_item

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=PatientCreated, status_code=201,
             responses={400: {"description": "Invalid input"}, 409: {"description": "Duplicate patient"}})
def register_patient(data: PatientCreate, db: Session = Depends(get_db)):
    return serialize_created_patient(create_patient(db, data))


@router.get("", response_model=PatientListResponse, responses={400: {"description": "Invalid query parameters"}})
def list_patients(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    db: Session = Depends(get_db),
):
    count, patients = repository.list_patients(db, page=page, page_size=page_size, search=search)
    return PatientListResponse(
        count=count, page=page, page_size=page_size,
        results=[serialize_patient_list_item(patient) for patient in patients],
    )
