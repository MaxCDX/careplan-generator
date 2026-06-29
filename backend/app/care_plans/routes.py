from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.care_plans import repository as care_plan_repository
from app.care_plans.schemas import CarePlanRead
from app.care_plans.serializers import serialize_care_plan
from app.database import get_db
from app.exceptions import NotFoundError

router = APIRouter(prefix="/care-plans", tags=["care-plans"])


@router.get("", response_model=list[CarePlanRead])
def list_care_plans(db: Session = Depends(get_db)):
    """Return all persisted generated care plans, newest first."""
    return [serialize_care_plan(care_plan) for care_plan in care_plan_repository.list_care_plans(db)]


@router.get("/{care_plan_id}", response_model=CarePlanRead)
def get_care_plan(care_plan_id: str, db: Session = Depends(get_db)):
    """Return one generated CarePlan by id."""
    care_plan = care_plan_repository.get_care_plan(db, care_plan_id)
    if not care_plan:
        raise NotFoundError(
            code="CARE_PLAN_NOT_FOUND",
            message="Care plan not found.",
        )
    return serialize_care_plan(care_plan)
