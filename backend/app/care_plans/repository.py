from sqlalchemy.orm import Session, joinedload

from app.care_plans.models import CarePlan
from app.orders.models import Order


def create_care_plan(db: Session, *, order: Order, care_plan_content: str, model: str) -> CarePlan:
    """Persist generated care plan content for a successfully processed Order."""
    care_plan = CarePlan(order_id=order.id, care_plan_content=care_plan_content, model=model)
    db.add(care_plan)
    db.commit()
    db.refresh(care_plan)
    return care_plan


def list_care_plans(db: Session) -> list[CarePlan]:
    """Load all generated CarePlans, newest first."""
    return (
        db.query(CarePlan)
        .options(joinedload(CarePlan.order))
        .order_by(CarePlan.created_at.desc())
        .all()
    )


def get_care_plan(db: Session, care_plan_id: str) -> CarePlan | None:
    """Load one CarePlan by id, or None when it does not exist."""
    return (
        db.query(CarePlan)
        .options(joinedload(CarePlan.order))
        .filter(CarePlan.id == care_plan_id)
        .one_or_none()
    )
