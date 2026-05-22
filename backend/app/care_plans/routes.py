import logging
import os
import time
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI
from sqlalchemy.orm import Session

from app.care_plans import repository as care_plan_repository
from app.care_plans.schemas import CarePlanGenerateRequest, CarePlanRead
from app.database import get_db
from app.care_plans.models import CarePlan
from app.orders import repository as order_repository

router = APIRouter(prefix="/care-plans", tags=["care-plans"])

MOCK_CARE_PLAN_CONTENT = """Problem list:
- Mock problem list for local care plan testing.

Goals:
- Mock goal for local care plan testing.

Pharmacist interventions:
- Mock pharmacist intervention for local care plan testing.

Monitoring plan:
- Mock monitoring plan for local care plan testing."""


def get_llm_provider() -> str:
    """Return the configured LLM provider, defaulting to real OpenAI."""
    return os.getenv("LLM_PROVIDER", "openai").lower()


def get_mock_llm_delay_secs() -> float:
    """Return optional mock LLM delay for local Celery-flow testing."""
    return float(os.getenv("MOCK_LLM_DELAY_SECS", "0"))


def generate_mock_care_plan_content() -> str:
    """Return deterministic mock care plan content for local development."""
    delay_secs = get_mock_llm_delay_secs()
    if delay_secs > 0:
        time.sleep(delay_secs)
    return MOCK_CARE_PLAN_CONTENT


def build_prompt(order) -> str:
    """Build the plain-text LLM prompt from an Order and its linked records.

    The prompt uses only fields currently stored on Order/Patient/Provider and
    asks the model to show placeholders instead of inventing missing facts.
    """
    today = date.today().isoformat()

    return f"""
You are generating a pharmacist-review draft care plan for a specialty pharmacy workflow.
This is NOT final medical advice. The output will be reviewed by a licensed pharmacist before use.

Use ONLY the provided order, patient, and provider information. Do not invent or assume missing clinical facts.
If a field is unavailable, use an explicit placeholder such as [NOT PROVIDED].

Available information:
- Generated date: {today}
- Patient name: {order.patient.name or "[NOT PROVIDED]"}
- Patient MRN: {order.patient.mrn or "[NOT PROVIDED]"}
- Medication: {order.medication or "[NOT PROVIDED]"}
- Referring provider: {order.provider.name or "[NOT PROVIDED]"}
- Referring provider NPI: {order.provider.npi or "[NOT PROVIDED]"}
- Diagnosis: {order.diagnosis or "[NOT PROVIDED]"}
- Clinical notes: {order.clinical_notes or "[NOT PROVIDED]"}

Missing information rules:
- If weight is needed, write [WEIGHT NOT PROVIDED].
- If medication history/current medications are needed, write [CURRENT MEDICATION LIST NOT PROVIDED].
- If allergies are needed, write [ALLERGIES NOT PROVIDED].
- If provider fax is needed, write [PROVIDER FAX NOT PROVIDED].
- If lab values are needed but not present in clinical notes, write [LAB VALUES NOT PROVIDED].
- If pharmacist license is needed, write [LICENSE NUMBER].
- Do not fabricate patient phone number, insurance details, provider fax, lab results, dates beyond the generated date, allergies, medication history, or weight.

Output requirements:
- Plain text only.
- No Markdown code fences.
- No JSON.
- No extra explanation before or after the care plan.
- Use the exact section headers and separator lines shown below.
- Keep recommendations general and tied to the provided diagnosis, medication, and clinical notes.

SPECIALTY PHARMACY CARE PLAN
Generated: {today}
Patient: {order.patient.name or "[NOT PROVIDED]"} (MRN: {order.patient.mrn or "[NOT PROVIDED]"})
Medication: {order.medication or "[NOT PROVIDED]"}
Referring Provider: {order.provider.name or "[NOT PROVIDED]"} (NPI: {order.provider.npi or "[NOT PROVIDED]"})

================================================================================
PROBLEM LIST / DRUG THERAPY PROBLEMS (DTPs)
================================================================================
[numbered list based only on the provided diagnosis, medication, and clinical notes]

================================================================================
GOALS (SMART)
================================================================================
PRIMARY GOAL:
[primary measurable therapy goal based on the provided diagnosis and medication]

SAFETY GOALS:
- [safety goal]
- [safety goal]

PROCESS GOALS:
- [process goal]
- [process goal]

================================================================================
PHARMACIST INTERVENTIONS / PLAN
================================================================================

1. DOSING & ADMINISTRATION
   - [recommend pharmacist verification of dose, route, frequency, and appropriateness]
   - If weight is required for dosing, state [WEIGHT NOT PROVIDED].

2. PREMEDICATION / ADMINISTRATION SUPPORT
   - [administration support considerations based on medication class when appropriate]

3. ADVERSE EVENT MONITORING
   - [monitoring considerations based on the medication and provided notes]

4. LABORATORY MONITORING SCHEDULE
   - [recommended monitoring categories]
   - Use [LAB VALUES NOT PROVIDED] if actual values are not included.

5. DRUG INTERACTION MANAGEMENT
   - [interaction review plan]
   - Use [CURRENT MEDICATION LIST NOT PROVIDED] if no medication list appears in the clinical notes.

6. PATIENT EDUCATION CHECKLIST
   [ ] [education item]
   [ ] [education item]
   [ ] [education item]

7. COORDINATION OF CARE
   - [coordination step with referring provider]
   - Provider fax: [PROVIDER FAX NOT PROVIDED]

================================================================================
MONITORING PLAN & FOLLOW-UP SCHEDULE
================================================================================
WEEK 1: [early tolerance/adherence follow-up]
WEEK 2: [continued tolerance/adherence follow-up]
WEEK 4: [clinical response and monitoring review]
WEEK 8: [refill/adherence and safety check]
WEEK 12: [therapy effectiveness and provider update]
ONGOING: [ongoing monitoring plan]

================================================================================
CLINICAL NOTES
================================================================================
[briefly summarize only the provided clinical notes and do not add unsupported facts]

Pharmacist Signature: _________________________ Date: {today}
RPh License #: [LICENSE NUMBER]

================================================================================
END OF CARE PLAN
================================================================================
""".strip()


def generate_care_plan_content(order, model: str) -> str:
    """Return generated care plan text using the configured LLM provider."""
    if get_llm_provider() == "mock":
        return generate_mock_care_plan_content()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(model=model, input=build_prompt(order))
    return response.output_text


def serialize_care_plan(care_plan: CarePlan) -> CarePlanRead:
    """Convert a CarePlan SQLAlchemy model into the public API response."""
    return CarePlanRead(
        id=care_plan.id,
        order_id=care_plan.order_id,
        model=care_plan.model,
        care_plan=care_plan.care_plan_content,
        created_at=care_plan.created_at,
    )


@router.post("", response_model=CarePlanRead)
def generate_care_plan(data: CarePlanGenerateRequest, db: Session = Depends(get_db)):
    """Directly generate and persist a CarePlan for an existing Order.

    The primary order-submission path is POST /orders -> Celery. This endpoint
    remains available as a manual synchronous generation path for a known Order.
    """
    order = order_repository.get_order(db, data.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.care_plan:
        raise HTTPException(status_code=409, detail="Care plan already exists for this order")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    # Order owns workflow status; CarePlan is only the generated artifact.
    order.status = "processing"
    order.error_message = None
    db.add(order)
    db.commit()
    db.refresh(order)

    try:
        logging.info("Starting LLM call for order %s", order.id)
        care_plan_content = generate_care_plan_content(order, model)
        # Persist generated content only after the LLM call succeeds.
        care_plan = care_plan_repository.create_care_plan(
            db,
            order=order,
            care_plan_content=care_plan_content,
            model=model,
        )
        order.status = "completed"
        order.error_message = None
        db.add(order)
        db.commit()
        logging.info("LLM call completed for order %s", order.id)
        return serialize_care_plan(care_plan)
    except Exception as exc:
        db.rollback()
        # Keep failed generation state durable so a restart does not erase it.
        order.status = "failed"
        order.error_message = str(getattr(exc, "detail", exc))[:1000]
        db.add(order)
        db.commit()
        raise HTTPException(
            status_code=getattr(exc, "status_code", 500),
            detail=f"Care plan generation failed: {getattr(exc, 'detail', exc)}",
        ) from exc


@router.get("", response_model=list[CarePlanRead])
def list_care_plans(db: Session = Depends(get_db)):
    """Return all persisted generated care plans, newest first."""
    return [serialize_care_plan(care_plan) for care_plan in care_plan_repository.list_care_plans(db)]


@router.get("/{care_plan_id}", response_model=CarePlanRead)
def get_care_plan(care_plan_id: str, db: Session = Depends(get_db)):
    """Return one generated CarePlan by id."""
    care_plan = care_plan_repository.get_care_plan(db, care_plan_id)
    if not care_plan:
        raise HTTPException(status_code=404, detail="Care plan not found")
    return serialize_care_plan(care_plan)
