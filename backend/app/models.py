"""SQLAlchemy models for persistent care plan workflow state."""

from uuid import uuid4

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from .database import Base


def new_uuid() -> str:
    """Return a string UUID for primary keys stored as String columns."""
    return str(uuid4())


class Patient(Base):
    """Reusable patient identity record keyed by MRN."""

    __tablename__ = "patients"

    id = Column(String(36), primary_key=True, default=new_uuid)
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100))
    last_name = Column(String(100), nullable=False)
    mrn = Column(String(20), nullable=False, unique=True, index=True)
    date_of_birth = Column(Date)
    sex = Column(String(10))
    weight_kg = Column(Numeric(5, 2))
    allergies = Column(Text)
    primary_diagnosis = Column(String(8))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def full_name(self):
        return " ".join(part for part in (self.first_name, self.middle_name, self.last_name) if part)

    orders = relationship("Order", back_populates="patient")
    diagnoses = relationship("PatientDiagnosis", back_populates="patient",
                             order_by="PatientDiagnosis.position", cascade="all, delete-orphan")
    medication_history = relationship("MedicationHistory", back_populates="patient",
                                      order_by="MedicationHistory.position", cascade="all, delete-orphan")


class PatientDiagnosis(Base):
    __tablename__ = "patient_diagnoses"
    __table_args__ = (UniqueConstraint("patient_id", "position"),)

    id = Column(String(36), primary_key=True, default=new_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    icd10_code = Column(String(8), nullable=False)
    position = Column(Integer, nullable=False)
    patient = relationship("Patient", back_populates="diagnoses")


class MedicationHistory(Base):
    __tablename__ = "medication_history"
    __table_args__ = (UniqueConstraint("patient_id", "position"),)

    id = Column(String(36), primary_key=True, default=new_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    medication_text = Column(Text, nullable=False)
    position = Column(Integer, nullable=False)
    patient = relationship("Patient", back_populates="medication_history")


class Provider(Base):
    """Reusable referring provider identity record keyed by NPI."""

    __tablename__ = "providers"

    id = Column(String(36), primary_key=True, default=new_uuid)
    name = Column(String(200), nullable=False)
    npi = Column(String(20), nullable=False, unique=True, index=True)

    orders = relationship("Order", back_populates="provider")


class Order(Base):
    """Durable workflow/request record for a care plan generation attempt.

    Order owns status because workflow state exists before a CarePlan is created
    and must still be persisted when generation fails.
    """

    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=new_uuid)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    provider_id = Column(String(36), ForeignKey("providers.id"), nullable=False, index=True)
    medication = Column(String(200), nullable=False)
    diagnosis = Column(String(500), nullable=False)
    clinical_notes = Column(Text, nullable=False)
    status = Column(String(30), nullable=False, default="queued", index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    patient = relationship("Patient", back_populates="orders")
    provider = relationship("Provider", back_populates="orders")
    care_plan = relationship("CarePlan", back_populates="order", uselist=False, cascade="all, delete-orphan")


class CarePlan(Base):
    """Generated care plan artifact linked to one successful Order.

    CarePlan stores generated content only; lifecycle status remains on Order.
    """

    __tablename__ = "care_plans"

    id = Column(String(36), primary_key=True, default=new_uuid)
    order_id = Column(String(36), ForeignKey("orders.id"), nullable=False, unique=True, index=True)
    care_plan_content = Column(Text, nullable=False)
    model = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    order = relationship("Order", back_populates="care_plan")
