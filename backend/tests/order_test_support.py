from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@contextmanager
def isolated_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )
    try:
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            app.dependency_overrides[get_db] = lambda: db
            try:
                yield TestClient(app), db
            finally:
                app.dependency_overrides.pop(get_db)
    finally:
        engine.dispose()


def order_payload(**overrides):
    return {
        "patient_first_name": "Test",
        "patient_last_name": "Patient",
        "patient_date_of_birth": "1979-06-08",
        "mrn": "123456",
        "provider_name": "Dr. Test",
        "provider_npi": "1234567890",
        "diagnosis": "G70.00",
        "medication": "IVIG",
        "clinical_notes": "Fictional clinical note.",
        **overrides,
    }
