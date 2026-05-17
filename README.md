# Care Plan Generator

> Current Status: Day 1 — Requirements Analysis & System Design

Care Plan Generator is a healthcare workflow system designed for specialty pharmacy staff.

The project is currently in the requirements-analysis and system-design phase. The planned system will allow medical assistants to submit patient, provider, medication-order, and clinical information so the backend can generate a pharmacist-reviewed care plan draft while preserving validation, duplicate-detection, and reporting requirements around the workflow.

---

## Problem Being Solved

Pharmacists currently spend about 20–40 minutes per patient creating care plans manually. These care plans are required for compliance and reimbursement, and the current workload creates backlog for an already short-staffed team.

---

## Current Project Status

**Day 1 — requirements analysis and system design only.**

The repository does not contain a runnable application yet. Day 1 is focused on clarifying requirements, documenting the intended architecture, and preparing the project for later implementation.

---

## Intended Users

- Medical assistants who enter patient, provider, order, and clinical information
- Pharmacists who review and use the generated care plan draft
- Providers whose information must remain consistent in the system
- Admin or reporting users who need exportable operational data

Patients are not direct users of the system.

---

## MVP Scope

The planned MVP will:

- accept patient, provider, medication-order, and clinical inputs
- validate required fields and healthcare identifiers before processing
- detect duplicate patients, orders, and providers
- distinguish warnings from blocking errors
- generate a downloadable care plan draft through an LLM provider abstraction
- preserve structured data for future pharma reporting exports

The MVP will not include a patient portal, EHR integration, insurance billing integration, advanced cloud deployment, or production PHI handling unless that requirement is explicitly confirmed later.

---

## Planned Architecture

The planned system architecture consists of:

- a React or Next.js frontend for structured intake workflows
- a Python backend API for validation, duplicate detection, and orchestration
- PostgreSQL for structured persistence
- an LLM integration layer for care plan generation
- asynchronous background processing in a later phase

---

## Planned Tech Stack

The following technologies are planned for later implementation:

- FastAPI backend
- React or Next.js frontend
- PostgreSQL database
- LLM provider abstraction
- Docker in a later phase
- Redis and Celery in a later phase

---

## Important Product Rules

- All inputs must be validated before processing.
- Duplicate detection must cover patients, medication orders, and providers.
- Warning cases may require user confirmation; error cases must block submission.
- The AI output is a human-reviewed draft, not the clinical source of truth.
- No real PHI should be committed to the repository or written to logs.

---

## Repository Structure

```text
careplan-generator/
└── README.md
```

Additional application directories will be introduced gradually as implementation begins.

---

## Development Roadmap

- Define requirements and system design
- Build a synchronous MVP flow
- Add database-backed persistence
- Introduce asynchronous care plan generation
- Add validation, duplicate detection, and tests
- Add reporting/export support
- Add monitoring and deployment support

---

## How to Run

There is no runnable application yet.

Day 1 is focused on requirements analysis, architecture planning, and project setup documentation before implementation begins.

---

## Safety and Compliance Note

This repository should use only fictional or de-identified data until the PHI handling scope is explicitly confirmed. Real PHI must not be committed, logged, or exposed in error messages.

---

This project is being developed incrementally with a strong focus on validation, workflow integrity, and safe AI-assisted healthcare operations.
