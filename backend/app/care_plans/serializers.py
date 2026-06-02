from app.care_plans.models import CarePlan
from app.care_plans.schemas import CarePlanRead


def serialize_care_plan(care_plan: CarePlan) -> CarePlanRead:
    """Convert a CarePlan SQLAlchemy model into the public API response."""
    return CarePlanRead(
        id=care_plan.id,
        order_id=care_plan.order_id,
        model=care_plan.model,
        care_plan=care_plan.care_plan_content,
        created_at=care_plan.created_at,
    )
