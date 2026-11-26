import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Order, Patient, Provider


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_order(db, **overrides):
    patient = Patient(first_name="Fictional", last_name="Patient", mrn="123456")
    provider = Provider(name="Fictional Provider", npi="1234567890")
    db.add_all([patient, provider])
    db.flush()
    order = Order(
        patient_id=patient.id,
        provider_id=provider.id,
        medication="IVIG",
        diagnosis="G70.00",
        clinical_notes="Fictional clinical note.",
        **overrides,
    )
    db.add(order)
    db.flush()
    db.refresh(order)
    return order


def test_order_defaults_to_queued_when_status_is_omitted(db):
    assert make_order(db).status == "queued"


@pytest.mark.parametrize("status", ["queued", "processing", "completed", "failed"])
def test_order_preserves_explicit_status(db, status):
    assert make_order(db, status=status).status == status
