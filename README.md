# Care Plan Generator

> Current Status: Day 8 — Async Workflow MVP with Validation, Duplicate Detection, Warning Confirmation, Testing, and CI

Care Plan Generator is a healthcare workflow system for specialty pharmacy staff. It lets an operator submit patient, provider, medication, diagnosis, and clinical-note information, then generates a pharmacist-review care plan draft using an LLM.

This project is not just a GPT wrapper. The main engineering focus is workflow correctness: durable state, clear domain boundaries, validation, duplicate detection, and safe AI-assisted drafting.

---

## What It Does Now

The current MVP supports a database-backed async workflow with validation, duplicate detection, warning confirmation, and background care plan generation:

```text
Frontend form
→ POST /orders
→ validate request format
→ run duplicate detection and business-rule checks
→ create/reuse Patient and Provider if request is clean or confirmed
→ create Order(status="queued")
→ dispatch Celery task
→ return HTTP 202 Accepted immediately
```

Order submission can return four intentional outcomes:

```text
400 Bad Request
→ request format is invalid, such as invalid NPI, MRN, DOB, or blank required fields

409 Conflict
→ business rule blocks the request, such as provider NPI conflict or same-day duplicate order

200 OK with warning
→ request may be valid but needs user confirmation, such as possible duplicate patient or different-day duplicate order

202 Accepted
→ request is accepted, Order is queued, and background generation starts
```

Warning confirmation flow:

```text
Backend returns warning
→ frontend shows warning panel
→ user can cancel and keep editing
→ user can continue anyway
→ frontend resubmits the same form with confirm=true
→ backend creates the Order and dispatches Celery
```

Frontend starts polling GET /orders/{id}/status every 3 seconds.

Celery worker consumes the task asynchronously.
Worker generates a CarePlan using an LLM.
Worker stores CarePlan in PostgreSQL.
Worker updates Order workflow state.

Order status transitions:
queued → processing → completed / failed

Frontend polling stops when:
- completed
- failed
- frontend timeout reached
```

If queue dispatch fails:

```text
Order(status="failed")
Order.error_message is saved
Job is not queued
```

Workflow state survives backend restarts because Orders are stored in PostgreSQL instead of Python process memory.

---

## Tech Stack

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, Pydantic, SQLAlchemy, OpenAI SDK
- Database: PostgreSQL
- Async Processing: Celery, Redis
- Infrastructure: Docker, Docker Compose, GitHub Actions CI

---

## Architecture

```text
┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────────┐
│ Frontend   │   │ Backend    │   │ Database   │   │ Worker     │
│ Next.js    │   │ FastAPI    │   │ PostgreSQL │   │ Celery     │
└─────┬──────┘   └─────┬──────┘   └─────┬──────┘   └─────┬──────┘
      │                │                │                │
      │ 1. Submit      │                │                │
      │───────────────▶│                │                │
      │                │ 2. Save order  │                │
      │                │───────────────▶│                │
      │                │ status=queued  │                │
      │                │                │                │
      │ 3. HTTP 202    │                │                │
      │◀───────────────│                │                │
      │                │                │                │
      │                │                │ 4. Take task   │
      │                │                │◀───────────────│
      │                │                │                │
      │                │                │ 5. Save result │
      │                │                │◀───────────────│
      │                │                │ status=done    │
      │                │                │                │
      │ 6. Poll status │                │                │
      │───────────────▶│ 7. Get status  │                │
      │                │───────────────▶│                │
      │                │◀───────────────│                │
      │ 8. Return wait │                │                │
      │◀───────────────│                │                │
      │                │                │                │
      │ (poll again)   │                │                │
      │                │                │                │
      │ 9. Poll status │                │                │
      │───────────────▶│10. Get status  │                │
      │                │───────────────▶│                │
      │                │◀───────────────│                │
      │11. Return done │                │                │
      │◀───────────────│                │                │
      │                │                │                │
      │12. Render      │                │                │
```

Technology responsibilities:

- Next.js frontend owns operator UI and polling behavior
- FastAPI owns API orchestration and workflow state transitions
- PostgreSQL owns durable workflow state and generated artifacts
- Redis acts as the Celery message broker
- Celery workers process long-running background LLM jobs

Current Day 8 async workflow:

```text
1. Next.js frontend submits form
2. FastAPI backend creates/reuses Patient and Provider
3. FastAPI backend creates Order(status="queued") in PostgreSQL
4. FastAPI backend dispatches Celery task through Redis
5. For invalid input, FastAPI returns a 400 validation error envelope
6. For blocking business conflicts, FastAPI returns a 409 error envelope
7. For confirmable warnings, FastAPI returns HTTP 200 with warning metadata
8. FastAPI backend immediately returns HTTP 202 Accepted
9. Next.js frontend starts polling GET /orders/{id}/status every 3 seconds
10. Celery worker consumes queued Redis task asynchronously
11. Celery worker updates Order.status from queued → processing
12. Celery worker generates CarePlan using mock or real LLM
13. Celery worker stores CarePlan and updates Order.status → completed in PostgreSQL
14. Next.js frontend polling detects completed status
15. Next.js frontend displays generated result
```

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
│ status: queued / processing / completed / failed  │
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
│       ├── main.py                  # FastAPI app setup and router registration
│       ├── database.py              # SQLAlchemy engine/session/Base
│       ├── models.py                # shared SQLAlchemy entities
│       ├── celery_app.py            # Celery configuration and Redis broker setup
│       ├── exceptions.py            # application exception types and error response metadata
│       │
│       ├── tasks/
│       │   └── care_plan_tasks.py   # Celery worker entrypoint and async workflow processing
│       │
│       ├── patients/
│       │   ├── repository.py        # patient lookup/create by MRN
│       │   ├── schemas.py           # patient DTOs
│       │   └── models.py            # feature-level model alias
│       │
│       ├── providers/
│       │   ├── repository.py        # provider lookup/create by NPI
│       │   ├── schemas.py           # provider DTOs
│       │   └── models.py            # feature-level model alias
│       │
│       ├── orders/
│       │   ├── routes.py            # HTTP endpoints for order APIs
│       │   ├── service.py           # order workflow orchestration + Celery dispatch
│       │   ├── repository.py        # order database operations
│       │   ├── serializers.py       # Order -> API response formatting
│       │   ├── schemas.py           # request/response DTOs
│       │   └── models.py            # feature-level model alias
│       │
│       └── care_plans/
│           ├── routes.py            # HTTP endpoints for care plan APIs
│           ├── service.py           # LLM provider selection and generation logic
│           ├── prompts.py           # prompt construction
│           ├── repository.py        # care plan database operations
│           ├── serializers.py       # CarePlan -> API response formatting
│           ├── schemas.py           # request/response DTOs
│           └── models.py            # feature-level model alias
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                 # top-level page orchestration and state ownership
│   │   └── layout.tsx               # root layout and metadata
│   │
│   ├── components/
│   │   ├── OrderForm.tsx            # presentational order submission form
│   │   ├── OrderStatus.tsx          # status/error/result state display
│   │   ├── CarePlanResult.tsx       # generated care plan rendering
│   │
│   ├── hooks/
│   │   └── useOrderPolling.ts       # polling lifecycle, timeout, cleanup logic
│   │
│   ├── lib/
│   │   └── api.ts                   # centralized frontend API calls
│   │
│   └── types/
│       └── orders.ts                # shared frontend request/response types
│
├── docker-compose.yml
├── .env.example
└── README.md
```

### Backend Layer Responsibilities

The backend follows a feature-based structure instead of a large global `controllers/`, `services/`, and `repositories/` layout.

Within each feature:

- `routes.py` owns HTTP request/response handling
- `service.py` owns workflow orchestration and business logic
- `repository.py` owns database access
- `serializers.py` owns API response formatting
- `schemas.py` owns Pydantic request/response DTOs
- `models.py` exposes feature-local model aliases
- `exceptions.py` defines expected application errors that are converted into a consistent API error envelope

This structure keeps related code close together while still separating HTTP boundaries, business logic, and persistence concerns.

---

## API

### `POST /orders`

Creates a durable async workflow request, dispatches a Celery background task, and immediately returns HTTP 202 Accepted.

```json
{
  "patient_name": "Example Patient",
  "patient_dob": "1980-01-01",
  "mrn": "123456",
  "provider_name": "Dr. Example Provider",
  "provider_npi": "0000000000",
  "diagnosis": "G70.00",
  "medication": "Example specialty medication",
  "clinical_notes": "Fictional demo note. This example contains no real patient, provider, or clinical information.",
  "confirm": false
}
```

`confirm` is used only after the backend returns a warning. A clean first submission should use `false` or omit it.

Possible `POST /orders` responses:

```text
202 Accepted
→ Order created and queued for background generation

200 OK
→ warning response requiring user confirmation before Order creation

400 Bad Request
→ request validation failed

409 Conflict
→ business rule blocked the request

503 Service Unavailable
→ Order was created but the queue dispatch failed
```

Current endpoints:

```text
POST /orders
GET /orders
GET /orders/{order_id}
GET /orders/{order_id}/status
```

---

## Validation, Duplicate Detection, and Warnings

The order submission flow performs checks before creating an Order or dispatching a Celery task.

Validation checks happen in Pydantic schemas before business logic runs:

```text
provider_npi must be exactly 10 digits
mrn must be exactly 6 digits
patient_dob must use YYYY-MM-DD when provided
required strings must not be blank
```

Duplicate detection and business checks happen in the order service layer:

```text
Provider: same NPI + different name
→ blocked with 409 PROVIDER_NPI_CONFLICT

Patient: same MRN + different name or DOB
→ warning, user confirmation required

Patient: same name + same DOB + different MRN
→ warning, user confirmation required

Order: same patient + same medication + same day
→ blocked with 409 DUPLICATE_ORDER_SAME_DAY

Order: same patient + same medication + different day
→ warning unless confirm=true
```

Warnings do not create an Order and do not dispatch Celery. After reviewing the warning, the frontend can resubmit the same form with `confirm=true`.

---

## Error Handling

Expected API errors use a consistent error envelope:

```json
{
  "status": "error",
  "code": "PROVIDER_NPI_CONFLICT",
  "message": "Provider NPI already belongs to a different provider name.",
  "detail": {}
}
```

Current error categories:

```text
400 VALIDATION_ERROR
→ request format is invalid

409 PROVIDER_NPI_CONFLICT
→ provider NPI already belongs to a different provider name

409 DUPLICATE_ORDER_SAME_DAY
→ duplicate order for the same patient and medication on the same day

404 ORDER_NOT_FOUND
→ requested order does not exist

503 CARE_PLAN_QUEUE_UNAVAILABLE
→ order could not be dispatched to the background worker
```

Warnings are intentionally not exceptions. They are normal business responses because the user can confirm and continue.

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
LLM_MODEL=gpt-4o-mini
LLM_PROVIDER=mock
MOCK_LLM_DELAY_SECS=2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg2://careplan:careplan@db:5432/careplan
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

`OPENAI_MODEL` remains supported as a legacy fallback when `LLM_MODEL` is not set.

Start the app:

```bash
docker compose up --build
```

Open:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
```

Run backend tests in Docker:

```bash
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:///:memory: backend sh -c "PYTHONPATH=. pytest tests"
```

Run backend tests locally without Docker:

```bash
cd backend
PYTHONPATH=. pytest tests
```

The backend test suite covers validation errors, patient/provider duplicate detection, warning responses, blocking conflicts, Celery dispatch behavior, and API integration paths.

---

## Continuous Integration

GitHub Actions runs the backend pytest suite on every push to `main` and every
pull request targeting `main`.

The workflow lives at `.github/workflows/backend-ci.yml`. It starts a PostgreSQL
service container, installs dependencies from `backend/requirements.txt`, and
runs:

```bash
PYTHONPATH=. pytest tests
```

The CI job provisions a clean PostgreSQL service container for each run. Tests create their own data and do not depend on local development data.

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
- SSE / WebSocket realtime push infrastructure
- distributed worker autoscaling
- dead-letter queue (DLQ)
- rate limiting / backpressure handling
- authentication and authorization
- audit logging and access tracing
- PDF upload and document extraction
- production PHI hardening
- monitoring and alerting
- production deployment pipeline
- frontend automated tests

These are intentionally deferred so each future architecture layer solves a real pain point.

---

## Core Summary

```text
Frontend submits intent.
Backend validates input before business logic.
Backend blocks invalid business conflicts before workflow creation.
Backend returns warnings for confirmable duplicate risks.
Frontend can resubmit warning flows with confirm=true.
Backend owns workflow state.
PostgreSQL owns durable state.
Redis acts as Celery broker.
Celery workers process background jobs.
Order owns lifecycle state.
CarePlan owns generated output.
Frontend polls workflow status every 3 seconds after accepted submissions.
Frontend timeout does not automatically mean backend failure.
GitHub Actions runs backend tests on pushes and pull requests.
```
