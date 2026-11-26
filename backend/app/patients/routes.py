from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import NotFoundError
from app.patients import repository
from app.patients.schemas import PatientCreate, PatientCreated, PatientDetail, PatientListResponse, PatientUpdate, PatientUpdated
from app.patients.service import create_patient, update_patient
from app.patients.serializers import serialize_created_patient, serialize_patient_detail, serialize_patient_list_item, serialize_updated_patient

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


@router.get("/{patient_id}", response_model=PatientDetail, responses={404: {"description": "Patient not found"}})
def get_patient_detail(patient_id: str, db: Session = Depends(get_db)):
    patient = repository.get_patient_detail(db, patient_id)
    if patient is None:
        raise NotFoundError(code="PATIENT_NOT_FOUND", message="Patient not found.")
    orders = repository.list_patient_orders(db, patient_id)
    return serialize_patient_detail(patient, orders)


@router.put("/{patient_id}", response_model=PatientUpdated, responses={
    400: {"description": "Invalid update"}, 404: {"description": "Patient not found"},
    409: {"description": "Patient identity conflict"},
})
def edit_patient(patient_id: str, data: PatientUpdate, db: Session = Depends(get_db)):
    """Update only supplied fields; MRN is immutable."""
    return serialize_updated_patient(update_patient(db, patient_id, data))
