# Care Plan Generator

> Current Status: Prometheus and Grafana Monitoring Complete

Care Plan Generator is a healthcare workflow system for specialty pharmacy staff. It lets an operator submit patient, provider, medication, diagnosis, and clinical-note information, then generates a pharmacist-review care plan draft using an LLM.

This project is not just a GPT wrapper. The main engineering focus is workflow correctness: durable state, clear domain boundaries, validation, duplicate detection, and safe AI-assisted drafting.

---

## What It Does Now

The current MVP provides:

- one canonical Order workflow for browser and partner submissions
- multi-source healthcare intake across JSON, XML, CSV, and Excel formats
- validation, duplicate detection, and warning confirmation before persistence
- asynchronous care plan generation through Redis and Celery
- pluggable Mock, OpenAI, and Claude LLM providers
- structured API errors and safe background failure messages
- Prometheus HTTP/runtime metrics with a provisioned Grafana dashboard

The primary browser workflow is:

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

See [order validation and duplicate rules](#validation-duplicate-detection-and-warnings) for the warning confirmation flow.

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

If queue dispatch fails:

```text
Order(status="failed")
Order.error_message is saved
Job is not queued
```

Workflow state survives backend restarts because Orders are stored in PostgreSQL instead of Python process memory.

Partner integrations submit source-specific payloads to `POST /external-orders/{source}`. The backend normalizes them into the same `OrderCreate` contract and reuses the complete Order workflow above.

---

## Tech Stack

- Frontend: Next.js, React, TypeScript
- Backend: FastAPI, Pydantic, SQLAlchemy, OpenAI SDK, Anthropic SDK
- Database: PostgreSQL
- Async Processing: Celery, Redis
- Architecture Patterns: Adapter Pattern, Factory Pattern
- Infrastructure: Docker, Docker Compose, GitHub Actions CI

---

## Architecture

### Primary Async Workflow

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
      │                │                │status=completed│
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
      │11. Completed   │                │                │
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

Current async workflow:

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

### Multi-source Intake Flow

```text
External Sources (JSON/XML/CSV/Excel)
            │
            ▼
     Adapter + Factory
            │
            ▼
    Canonical OrderCreate
            │
            ▼
 Existing Order Workflow
```

All external sources normalize into the canonical `OrderCreate` schema before entering the existing async workflow.

| Source | Format |
| --- | --- |
| `clinic_b` | Nested JSON |
| `pharmacorp` | XML |
| `healthfirst` | CSV |
| `enterprise_spreadsheet` | Excel |

Spreadsheet ingestion currently uses backend-side file paths for demonstration and testing. Browser-based file upload is not yet implemented.

### LLM Provider Architecture

```text
build_prompt(order)
          │
          ▼
   get_llm_service()
          │
          ▼
      LLM Factory
          │
   ┌──────┼──────┐
   ▼      ▼      ▼
 Mock  OpenAI Claude
```

Business workflow code remains provider-agnostic.

---

## Database Design

```text
┌──────────────┐        ┌──────────────┐
│   Patient    │        │   Provider   │
├──────────────┤        ├──────────────┤
│ id           │        │ id           │
│ first_name   │        │ name         │
│ mrn          │        │ npi          │
│ last_name    │        └──────┬───────┘
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
Patient  1 → many PatientDiagnosis rows (additional ICD-10 codes)
Patient  1 → many MedicationHistory rows (medication text)
Provider 1 → many Orders
Order    1 → zero or one CarePlan
```

`Order` owns workflow state. `CarePlan` owns generated output. Status belongs on `Order` because `queued`, `processing`, and `failed` can happen before a care plan exists.

---

## Project Structure

```text
careplan-generator/
├── backend/
│   ├── app/
│   │   ├── external_orders/         # source adapters, factory, and intake API
│   │   ├── llm/                     # provider interface, factory, and services
│   │   ├── orders/                  # canonical workflow and persistence
│   │   ├── care_plans/              # prompts, generated artifacts, read APIs
│   │   ├── patients/                # patient identity and persistence
│   │   ├── providers/               # provider identity and persistence
│   │   └── tasks/                   # Celery worker processing
│   └── tests/
│       ├── external_orders/         # source normalization and error tests
│       └── llm/                     # provider and factory tests
├── frontend/                        # Next.js form, polling, and result UI
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

Submit an order. A successful `202 Accepted` response includes the order ID for polling `GET /orders/{order_id}/status`.

```json
{
  "patient_first_name": "Example",
  "patient_middle_name": null,
  "patient_last_name": "Patient",
  "patient_date_of_birth": "1980-01-01",
  "mrn": "123456",
  "provider_name": "Dr. Example Provider",
  "provider_npi": "0000000000",
  "diagnosis": "G70.00",
  "medication": "Example specialty medication",
  "clinical_notes": "Fictional demo note. This example contains no real patient, provider, or clinical information.",
  "confirm": false
}
```

A `200` warning means the Order has not been created. After reviewing the warning, resubmit with `confirm=true` to continue.

Order clients upgrading from the single-name contract must replace `patient_name`
and `patient_dob` in submission bodies with the structured fields above.
`GET /orders?patient_name=...` still searches the full display name.

### `POST /patients`

Register a patient with `first_name`, `last_name`, a six-digit `mrn` string, and `primary_diagnosis`. Success returns `201` with the patient UUID. An existing MRN or a matching first name, last name and known birth date returns `409` with `detail.existing_patient_id`.

This schema replaces the old single-name layout. Existing development databases
require a schema reset before startup; resetting deletes local records. create_all does not alter
existing tables. Verify the local DB target and its postgres_data volume before
removing data. Preserve Prometheus and Grafana volumes.

### `GET /patients`

List patients or search by full name, e.g. `GET /patients?search=Smith&page=1&page_size=20`.
The response includes the total match count and a page of patient summaries with `full_name`.

### Other endpoints

`POST /providers` registers a name and a 10-digit NPI string (201).
For `409 PROVIDER_POSSIBLE_DUPLICATE`, review the existing provider ID and NPI
in `detail`; resubmit with `confirm: true` to register a distinct provider.
`409 PROVIDER_NPI_CONFLICT` always blocks creation.

| Endpoint | Purpose |
| --- | --- |
| `GET /patients/{patient_id}` | Read a patient profile with additional diagnoses, medication history, and order summaries (newest first). |
| `GET /patients/{patient_id}/orders` | Get the patient's UUID, full name and all order summaries, newest first. |
| `PUT /patients/{patient_id}` | Update supplied fields, e.g. `{"weight_kg":75}`. MRN is immutable. Supplied diagnosis and medication lists replace their previous contents; `[]` clears them. Returns an update summary with `updated_at`. |
| `DELETE /patients/{patient_id}` | Delete a patient with no orders and their diagnosis and medication rows (204). Active orders return 409 with `detail.active_orders`; historical orders also block deletion. An unknown patient returns 404. |
| `POST /external-orders/{source}` | Submit a partner payload through the same Order workflow. |
| `GET /orders/{order_id}` | Read one Order with patient and provider details. |
| `GET /orders/{order_id}/status` | Poll background generation status. |
| `GET /care-plans` · `GET /care-plans/{care_plan_id}` | List or retrieve generated care plans. |

See [interactive API docs](http://localhost:8000/docs) for request and response schemas when running locally.

---

## Orders List Pagination and Filtering

`GET /orders?status=failed&patient_name=John` lists matching orders, newest first.
Optional `patient_id` and `provider_id` filters accept UUIDs. All supplied filters use AND.

Both patient and order lists return `{count, page, page_size, results}`. `count` is the filtered total before pagination. Pages start at 1, default to 20 items, and allow up to 100 items. A page past the last match returns an empty `results` array.

---

## Validation, Duplicate Detection, and Warnings

The order submission flow performs checks before creating an Order or dispatching a Celery task.

Validation checks happen in Pydantic schemas before business logic runs:

```text
provider_npi must be exactly 10 digits
mrn must be exactly 6 digits
patient_date_of_birth must use YYYY-MM-DD when provided
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

400 INVALID_EXTERNAL_ORDER
→ an external source payload could not be parsed or normalized

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

External parsing details and background provider failures are not exposed to clients. Asynchronous generation failures are stored and returned as safe user-facing messages.

---

## How to Run

Create a local environment file:

```bash
cp .env.example .env
```

Example Docker values:

```env
LLM_PROVIDER=mock
LLM_MODEL=mock-model
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
MOCK_LLM_DELAY_SECS=2
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg2://careplan:careplan@db:5432/careplan
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
```

Supported values are `LLM_PROVIDER=mock|openai|claude`. `OPENAI_API_KEY` is required only for the OpenAI provider, while `ANTHROPIC_API_KEY` is required only for the Claude provider. Set `LLM_MODEL` to a model supported by the selected provider.

`OPENAI_MODEL` remains supported as a legacy fallback when `LLM_MODEL` is not set.

Start the app:

```bash
docker compose up --build
```

Open:

```text
Frontend: http://localhost:3000
Backend:  http://localhost:8000
Metrics:  http://localhost:8000/metrics
Prometheus: http://localhost:9090
Grafana: http://localhost:3001 (local default: admin/admin)
```

## Local Monitoring

Prometheus scrapes the FastAPI backend every 15 seconds. Grafana automatically
provisions the Prometheus datasource and the **Care Plan Generator Overview**
dashboard when the Compose stack starts.

The dashboard shows request rate by normalized FastAPI route template, response
status outcomes, p95 request latency, 4xx/5xx rate, in-progress requests,
backend process CPU/memory when supported by the container runtime, and the
Prometheus backend target status.

Metrics never use raw request paths or healthcare/business identifiers as
labels. The `/metrics` endpoint is excluded from request instrumentation.
Prometheus is operational telemetry only; PostgreSQL remains the source of
truth for Order workflow state and CarePlan artifacts.

Run backend tests in Docker:

```bash
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:///:memory: backend sh -c "PYTHONPATH=. pytest tests"
```

Run backend tests locally without Docker:

```bash
cd backend
PYTHONPATH=. pytest tests
```

The backend suite covers validation, duplicate detection, warning and conflict flows, external adapters, LLM providers, Celery processing, API integration, and metrics behavior. Orders list tests cover database filtering, filtered totals, page boundaries, and deterministic ordering.

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
- alerting, distributed tracing, and worker/container exporters
- production deployment pipeline
- frontend automated tests

These are intentionally deferred so each future architecture layer solves a real pain point.

---

## Core Summary

```text
Frontend submits intent.
External sources normalize into the canonical OrderCreate contract.
Backend validates input before business logic.
Backend blocks invalid business conflicts before workflow creation.
Backend returns warnings for confirmable duplicate risks.
Frontend can resubmit warning flows with confirm=true.
Backend owns workflow state.
PostgreSQL owns durable state.
Redis acts as Celery broker.
Celery workers process background jobs.
The LLM factory selects Mock, OpenAI, or Claude through configuration.
Order owns lifecycle state.
CarePlan owns generated output.
Frontend polls workflow status every 3 seconds after accepted submissions.
Frontend timeout does not automatically mean backend failure.
GitHub Actions runs backend tests on pushes and pull requests.
Prometheus scrapes normalized FastAPI request/runtime metrics.
Grafana provisions a local overview dashboard from version-controlled files.
```
