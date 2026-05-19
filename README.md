# Care Plan Generator

> Current Status: Day 3 — PostgreSQL-backed Workflow MVP

Care Plan Generator is a healthcare workflow system for specialty pharmacy staff. It lets an operator submit patient, provider, medication, diagnosis, and clinical-note information, then generates a pharmacist-review care plan draft using an LLM.

This project is not just a GPT wrapper. The main engineering focus is workflow correctness: durable state, clear domain boundaries, validation, duplicate detection, and safe AI-assisted drafting.

---

## What It Does Now

The current MVP supports a database-backed workflow:

```text
Frontend form
→ POST /orders
→ create/reuse Patient and Provider
→ create Order(status="pending")
→ POST /care-plans
→ update Order(status="processing")
→ call OpenAI synchronously
→ create CarePlan
→ update Order(status="completed")
→ display generated care plan
```

If generation fails:

```text
Order(status="failed")
Order.error_message is saved
CarePlan is not created
```

This means generated workflow state survives backend restarts because records are stored in PostgreSQL instead of Python memory.

---

## Tech Stack

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, Pydantic, SQLAlchemy, OpenAI SDK
- Database: PostgreSQL
- Infrastructure: Docker, Docker Compose

---

## Architecture

```text
Browser / Next.js
        ↓ HTTP
FastAPI backend
        ↓ SQLAlchemy
PostgreSQL

FastAPI backend
        ↓ OpenAI API
LLM-generated pharmacist-review draft
```

The frontend never talks directly to PostgreSQL or OpenAI. The backend owns workflow state transitions, persistence, and LLM orchestration.

---

## Database Design

```text
┌──────────────┐        ┌──────────────┐
│   Patient    │        │   Provider   │
├──────────────┤        ├──────────────┤
│ id           │        │ id           │
│ name         │        │ name         │
│ mrn          │        │ npi          │
│ dob          │        └──────┬───────┘
└──────┬───────┘               │
       │                       │
       ▼                       ▼
┌────────────────────────────────────────────┐
│                   Order                    │
├────────────────────────────────────────────┤
│ id                                         │
│ patient_id  → patients.id                  │
│ provider_id → providers.id                 │
│ medication                                 │
│ diagnosis                                  │
│ clinical_notes                             │
│ status: pending / processing / completed / failed │
│ error_message                              │
│ created_at                                 │
│ updated_at                                 │
└─────────────────────┬──────────────────────┘
                      │
                      ▼
┌────────────────────────────────────────────┐
│                 CarePlan                   │
├────────────────────────────────────────────┤
│ id                                         │
│ order_id → orders.id                       │
│ care_plan_content                          │
│ model                                      │
│ created_at                                 │
└────────────────────────────────────────────┘
```

Relationship summary:

```text
Patient  1 → many Orders
Provider 1 → many Orders
Order    1 → zero or one CarePlan
```

`Order` owns workflow state. `CarePlan` owns generated output. Status belongs on `Order` because `pending`, `processing`, and `failed` can happen before a care plan exists.

---

## Project Structure

```text
careplan-generator/
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app setup and router registration
│       ├── database.py      # SQLAlchemy engine/session/Base
│       ├── models.py        # Patient, Provider, Order, CarePlan tables
│       ├── patients/        # patient schemas/repository aliases
│       ├── providers/       # provider schemas/repository aliases
│       ├── orders/          # /orders routes, schemas, repository
│       └── care_plans/      # /care-plans routes, prompt, repository
├── frontend/
│   └── app/page.tsx         # form UI and two-step API flow
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API

### `POST /orders`

Creates a durable order/request record.

```json
{
  "patient_name": "Example Patient",
  "mrn": "MRN-EXAMPLE-001",
  "provider_name": "Dr. Example Provider",
  "provider_npi": "0000000000",
  "diagnosis": "Example diagnosis for demo purposes only",
  "medication": "Example specialty medication",
  "clinical_notes": "Fictional demo note. This example contains no real patient, provider, or clinical information."
}
```

### `POST /care-plans`

Generates a care plan for an existing order.

```json
{
  "order_id": "order-uuid"
}
```

Other endpoints:

```text
GET /orders
GET /orders/{order_id}
GET /care-plans
GET /care-plans/{care_plan_id}
```

---

## LLM Output Safety

The prompt generates a structured specialty pharmacy care plan draft and includes guardrails:

- output is for pharmacist review, not final medical advice
- use only provided patient/provider/order information
- do not fabricate missing clinical facts
- use placeholders such as `[WEIGHT NOT PROVIDED]`, `[LAB VALUES NOT PROVIDED]`, and `[LICENSE NUMBER]`

Missing clinical data should stay visibly missing. A placeholder is safer than a plausible hallucination.

---

## How to Run

Create a local environment file:

```bash
cp .env.example .env
```

Add your real OpenAI API key to `.env`.

Example Docker values:

```env
OPENAI_API_KEY=your_real_key_here
OPENAI_MODEL=gpt-4o-mini
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg2://careplan:careplan@db:5432/careplan
```

Start the app:

```bash
docker compose up --build
```

Open:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
```

---

## Inspect the Database

TablePlus connection:

```text
Host: localhost
Port: 5432
User: careplan
Password: careplan
Database: careplan
```

Useful commands:

```bash
docker compose exec db psql -U careplan -d careplan -c "select count(*) from patients; select count(*) from providers; select count(*) from orders; select count(*) from care_plans;"
```

Reset local database:

```bash
docker compose down -v
docker compose up --build
```

Warning: `down -v` deletes all local PostgreSQL volume data.

---

## Compliance Considerations

The repository should use only fictional or de-identified example data.

Production healthcare deployment would require additional compliance and operational controls, including:

- HIPAA-compliant infrastructure
- PHI encryption at rest and in transit
- audit logging and access tracing
- role-based access control (RBAC)
- secure secret management
- retention and deletion policies
- vendor/compliance review for external LLM providers
- monitoring and incident response workflows

The generated care plan is a pharmacist-review draft and not final medical advice.

## Current Limitations

Not implemented yet:

- Alembic migrations
- strict validation
- duplicate detection
- Redis/Celery background generation
- polling or WebSocket status updates
- authentication
- audit logging
- PDF upload
- production PHI handling
- monitoring/deployment

These are intentionally deferred so each future architecture layer solves a real pain point.

---

## Core Summary

```text
Frontend submits intent.
Backend owns workflow.
PostgreSQL owns durable state.
Order owns lifecycle.
CarePlan owns generated output.
```