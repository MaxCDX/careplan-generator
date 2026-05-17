import os
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

care_plans: list[dict] = []


class CarePlanRequest(BaseModel):
    patient_name: str
    mrn: str
    provider_name: str
    provider_npi: str
    diagnosis: str
    medication: str
    clinical_notes: str


class CarePlanResponse(BaseModel):
    id: str
    care_plan: str


def build_prompt(request: CarePlanRequest) -> str:
    return f"""
Generate a pharmacist-style draft care plan for pharmacist review only, not final medical advice.

Use exactly these sections:
1. Problem List
2. Goals
3. Pharmacist Interventions
4. Monitoring Plan

Patient information:
- Patient name: {request.patient_name}
- MRN: {request.mrn}
- Provider name: {request.provider_name}
- Provider NPI: {request.provider_npi}
- Diagnosis: {request.diagnosis}
- Medication: {request.medication}
- Clinical notes: {request.clinical_notes}
""".strip()


@app.post("/care-plans/generate", response_model=CarePlanResponse)
def generate_care_plan(request: CarePlanRequest):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is missing.")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        response = client.responses.create(
            model=model,
            input=build_prompt(request),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OpenAI request failed: {exc}") from exc

    care_plan = response.output_text
    record = {
        "id": str(uuid4()),
        **request.model_dump(),
        "care_plan": care_plan,
    }
    care_plans.append(record)

    return CarePlanResponse(id=record["id"], care_plan=care_plan)


@app.get("/care-plans")
def list_care_plans():
    return care_plans
