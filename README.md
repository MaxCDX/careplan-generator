# Care Plan Generator

> Current Status: Day 7 — Refactored Polling-based Async Workflow MVP

Care Plan Generator is a healthcare workflow system for specialty pharmacy staff. It lets an operator submit patient, provider, medication, diagnosis, and clinical-note information, then generates a pharmacist-review care plan draft using an LLM.

This project is not just a GPT wrapper. The main engineering focus is workflow correctness: durable state, clear domain boundaries, validation, duplicate detection, and safe AI-assisted drafting.

---

## What It Does Now

The current MVP supports a database-backed async workflow:

```text
Frontend form
→ POST /orders
→ create/reuse Patient and Provider
→ create Order(status="queued")
→ dispatch Celery task
→ return HTTP 202 Accepted immediately

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
- Infrastructure: Docker, Docker Compose

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

Current Day 7 refactored async workflow:

```text
1. Next.js frontend submits form
2. FastAPI backend creates/reuses Patient and Provider
3. FastAPI backend creates Order(status="queued") in PostgreSQL
4. FastAPI backend dispatches Celery task through Redis
5. FastAPI backend immediately returns HTTP 202 Accepted
6. Next.js frontend starts polling GET /orders/{id}/status every 3 seconds
7. Celery worker consumes queued Redis task asynchronously
8. Celery worker updates Order.status from queued → processing
9. Celery worker generates CarePlan using mock or real LLM
10. Celery worker stores CarePlan and updates Order.status → completed in PostgreSQL
11. Next.js frontend polling detects completed status
12. Next.js frontend displays generated result
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
│   │   └── CarePlanResult.tsx       # generated care plan rendering
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

This structure keeps related code close together while still separating HTTP boundaries, business logic, and persistence concerns.

---

## API

### `POST /orders`

Creates a durable async workflow request, dispatches a Celery background task, and immediately returns HTTP 202 Accepted.

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

Current endpoints:

```text
POST /orders
GET /orders
GET /orders/{order_id}
GET /orders/{order_id}/status
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
LLM_PROVIDER=mock
MOCK_LLM_DELAY_SECS=2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg2://careplan:careplan@db:5432/careplan
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
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
- frontend currently uses polling instead of realtime push updates
- no SSE / WebSocket realtime push infrastructure yet
- no distributed worker autoscaling yet
- no dead-letter queue (DLQ)
- no rate limiting / backpressure handling
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
Backend owns workflow state.
PostgreSQL owns durable state.
Redis acts as Celery broker.
Celery workers process background jobs.
Order owns lifecycle state.
CarePlan owns generated output.
Frontend polls workflow status every 3 seconds.
Frontend timeout does not automatically mean backend failure.
```