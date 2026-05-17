# Care Plan Generator

> Current Status: Day 2 — Minimal Synchronous MVP

Care Plan Generator is a healthcare workflow system designed for specialty pharmacy staff.

The system allows medical assistants to submit patient, provider, medication-order, and clinical information so the backend can generate a pharmacist-reviewed care plan draft while preserving workflow integrity and preparing for future validation, duplicate-detection, and reporting requirements.

---

## Problem Being Solved

Pharmacists currently spend about 20–40 minutes per patient creating care plans manually. These care plans are required for compliance and reimbursement, and the current workload creates operational backlog for already short-staffed teams.

The goal of this project is not simply AI text generation. The long-term goal is to build a reliable healthcare workflow system around validation, duplicate detection, structured operational data, and AI-assisted drafting.

---

## Current Project Status

The project currently contains a runnable Day 2 MVP.

The MVP demonstrates a complete synchronous workflow:

```text
Frontend form
→ FastAPI backend
→ OpenAI synchronous generation
→ in-memory storage
→ frontend displays generated care plan
```

Current implementation includes:

- FastAPI backend
- Next.js frontend
- OpenAI integration
- Docker Compose setup
- in-memory care plan storage
- local development workflow

---

## Intended Users

- Medical assistants who enter patient, provider, order, and clinical information
- Pharmacists who review and use the generated care plan draft
- Providers whose information must remain consistent in the system
- Admin or reporting users who need exportable operational data

Patients are not direct users of the system.

---

## Current MVP Scope

The current MVP can:

- accept patient, provider, medication, and clinical-note inputs
- synchronously generate a pharmacist-style care plan draft using OpenAI
- display the generated care plan in the frontend
- store generated records temporarily in backend memory

The current MVP intentionally does NOT yet include:

- PostgreSQL persistence
- strict validation rules
- duplicate detection
- warning vs blocking error handling
- Redis/Celery background jobs
- WebSocket or polling status updates
- authentication
- PDF upload
- EHR integration
- insurance/billing integration
- production PHI handling
- monitoring or cloud deployment

These features will be added incrementally in later phases.

---

## Planned Architecture

The planned long-term architecture consists of:

- a Next.js frontend for structured intake workflows
- a Python FastAPI backend for validation, orchestration, and workflow control
- PostgreSQL for structured persistence
- an LLM integration layer for care plan generation
- asynchronous background processing in later phases
- future reporting/export workflows

---

## Current Tech Stack

### Backend

- FastAPI
- Pydantic
- OpenAI SDK
- python-dotenv
- Uvicorn

### Frontend

- Next.js
- React
- TypeScript

### Infrastructure

- Docker
- Docker Compose

---

## Important Product Rules

- AI output is a pharmacist-reviewed draft, not the clinical source of truth.
- Real PHI must not be committed to the repository or exposed in logs.
- Validation and duplicate detection are core workflow requirements, even if not fully implemented yet.
- Workflow integrity matters more than UI polish.

---

## Repository Structure

```text
careplan-generator/
├── backend/
├── frontend/
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## How to Run

### Docker Compose

1. Create your env file:

```bash
cp .env.example .env
```

2. Add your real `OPENAI_API_KEY` to `.env`.

3. Start the application:

```bash
docker compose up --build
```

4. Open:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Stored records: http://localhost:8000/care-plans

---

## Local Development Without Docker

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-4o-mini
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

In a second terminal:

```bash
cd frontend
npm install
export NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

## API

### `POST /care-plans/generate`

Example request:

```json
{
  "patient_name": "John Doe",
  "mrn": "123456",
  "provider_name": "Dr. Smith",
  "provider_npi": "1234567890",
  "diagnosis": "Type 2 diabetes",
  "medication": "Metformin",
  "clinical_notes": "Patient has type 2 diabetes and needs a care plan."
}
```

Example response:

```json
{
  "id": "uuid",
  "care_plan": "generated text"
}
```

### `GET /care-plans`

Returns all generated records currently held in memory.

---

## Current MVP Limitations

The current system is intentionally naive so later architectural improvements are motivated by real operational pain points.

Current limitations include:

- synchronous OpenAI requests block the user request
- generated records disappear after backend restart
- no persistent database
- no job tracking
- no retry system
- no structured validation pipeline
- no duplicate-detection workflow
- unstructured LLM output formatting

These limitations are intentional learning steps before introducing more advanced infrastructure.

---

## Development Roadmap

- Requirements analysis and system design
- Build synchronous MVP workflow
- Add PostgreSQL persistence
- Introduce validation and duplicate detection
- Add asynchronous care plan generation
- Add reporting/export support
- Add monitoring and deployment support

---

## Safety and Compliance Note

This repository should use only fictional or de-identified data until PHI handling scope is explicitly confirmed.

Real PHI must never be committed, logged, or exposed in error messages.

---

This project is being developed incrementally with a strong focus on validation, workflow integrity, operational correctness, and safe AI-assisted healthcare workflows.