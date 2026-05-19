# System Design — Care Plan Generator

## 1. Overview

Care Plan Generator is intended to reduce the manual burden of creating care plans for specialty pharmacy workflows. Medical assistants enter patient, provider, medication-order, and clinical information; the system validates that data, applies duplicate-detection rules, and produces a downloadable care plan draft for pharmacist review.

This is not just a “GPT text generator.” The value of the system is the workflow around the draft: structured intake, data integrity, duplicate prevention, safe warning/error behavior, controlled output shape, and a foundation for reporting. The LLM is one component inside a healthcare workflow system, not the system of record.

## 2. Goals

- Generate care plan drafts from patient, order, and clinical inputs.
- Validate all inputs before processing.
- Detect duplicate patients, orders, and providers.
- Support safe warning and error behavior.
- Support downloadable care plan output.
- Support future pharma reporting export.

## 3. Non-goals for MVP

- No patient-facing portal.
- No real EHR integration yet.
- No insurance billing integration.
- No production PHI handling yet unless explicitly confirmed.
- No advanced deployment, AWS, or Terraform yet.
- No WebSocket or async worker on Day 1.

## 4. Users / Actors

- **Medical assistant:** enters patient, provider, medication-order, and clinical data.
- **Pharmacist:** reviews the generated care plan draft before use.
- **Provider:** represented in the system as a referenced clinical actor whose identity must stay consistent.
- **Admin/reporting user:** exports structured data for downstream pharma reporting.
- **Patient:** not a direct system user.

## 5. Core Workflow

1. A medical assistant enters patient, provider, medication-order, and clinical data.
2. The backend validates all submitted inputs.
3. The backend checks patient, order, and provider duplicate rules.
4. If an **ERROR** rule matches, submission is blocked.
5. If a **WARNING** rule matches, the user may confirm and continue according to policy.
6. The backend calls the LLM to generate a care plan draft.
7. The user downloads the care plan output.
8. Future reporting exports can use the structured system data captured during the workflow.

## 6. Domain Model Draft

- **Patient:** the person receiving care, identified by MRN and demographic attributes needed for duplicate checks and care plan context.
- **Provider:** the referring clinician, identified by NPI and display name.
- **MedicationOrder:** a request for one medication for one patient, including clinical context and the date needed for duplicate-detection rules.
- **CarePlan:** the generated pharmacist-review draft associated with one medication order.
- **DuplicateCheckResult:** a conceptual result object describing whether the submission is safe, requires confirmation, or must be blocked.
- **ExportReport:** a future reporting artifact built from structured patient, provider, order, and care-plan data.

## 7. Duplicate Detection Rules

| Scenario | Result |
|---|---|
| Same patient + same medication + same date | **ERROR** — block submission |
| Same patient + same medication + different date | **WARNING** — allow confirmation flow |
| Same MRN + different name or DOB | **WARNING** — possible data-entry issue |
| Same name + DOB + different MRN | **WARNING** — possible duplicate patient |
| Same NPI + different provider name | **ERROR** — provider identity conflict |

## 8. Validation Rules

- NPI must be exactly 10 digits.
- MRN must be exactly 6 digits according to the hard requirement in `requirement.md`; however, the sample data shows `00012345`, which is 8 digits and should be clarified before implementation.
- ICD-10 format should be validated.
- Required fields cannot be empty.
- Patient records may be provided as a string or PDF document.
- LLM input must be structured and sanitized before generation.

## 9. LLM Boundary

The LLM generates a care plan draft; it is not the clinical source of truth. The backend schema and business rules control what data is accepted and what output sections are required.

Every care plan must contain:

- Problem list
- Goals
- Pharmacist interventions
- Monitoring plan

LLM failures must be handled safely. The system should return a controlled failure state without exposing stack traces or unnecessary PHI to users, logs, or downstream clients.

## 10. API Design Draft

This is a conceptual API sketch only; no implementation exists yet.

- `POST /care-plans` — submit intake data and request care plan generation
- `GET /care-plans/{id}` — retrieve a generated care plan draft and its status
- `GET /providers` — retrieve known providers for reuse or review
- `POST /exports/pharma-report` — request a reporting export

Additional endpoints may be introduced later if the domain is split into patients, providers, and orders as separate resources.

## 11. Data Flow

1. The user submits the web form.
2. The backend parses the request and validates required fields and formats.
3. The backend runs duplicate checks across patient, provider, and medication-order data.
4. Blocking errors stop the workflow; warnings return a confirmation path.
5. On a valid submission, the backend builds a structured, sanitized LLM input.
6. The LLM returns a care plan draft in the required shape.
7. The backend stores or returns the draft according to the implementation stage.
8. The user downloads the care plan output.
9. Structured records remain available for later export/reporting use.

## 12. Error Handling Strategy

- **Validation error:** malformed or missing input; return a clear client-facing message and do not continue processing.
- **Duplicate warning:** suspicious but potentially valid submission; return a warning state that can be acknowledged if policy allows.
- **Duplicate blocking error:** known integrity conflict; stop processing until corrected.
- **LLM failure:** return a safe generation failure state without stack traces or unnecessary PHI exposure.
- **File parsing failure:** if PDF input cannot be read or validated, return a controlled parsing error and do not send malformed content to the LLM.

## 13. Testing Strategy

- Unit tests for validators.
- Unit tests for duplicate-detection rules.
- Integration tests for the `POST` / `GET` care plan flow.
- Mocked LLM tests for successful generation and failure paths.
- Error-handling tests for validation failures, duplicate warnings, duplicate blocking errors, LLM failures, and file parsing failures.

## 14. Reference Codebase Lessons

The reference project provides useful architectural lessons:

- **Separation of concerns:** patient, provider, order, care-plan, and report responsibilities are separated instead of being mixed into one module.
- **Validation layer:** healthcare identifiers are validated before deeper processing.
- **Service boundaries:** duplicate-detection and generation logic are separated from request handling.
- **Export/reporting patterns:** reporting is treated as a first-class downstream use case rather than an afterthought.
- **Background job pattern:** async generation exists in the reference implementation and is useful for later days once synchronous generation becomes a visible bottleneck.

Patterns not to blindly copy:

- Do not copy code directly from the reference project.
- Do not import advanced infrastructure into Day 1 merely because it exists there.
- Do not assume PHI safety just because logging is structured; logs must be explicitly designed to avoid sensitive data leakage.
- Do not let prior LLM outputs silently define future clinical structure without a deliberate product decision.

## 15. Day-by-Day Roadmap Alignment

- **Day 1:** documentation only — requirements, open questions, design.
- **Day 2:** synchronous MVP flow.
- **Day 3:** database design.
- **Day 4:** queue introduction.
- **Day 5:** worker processing.
- **Day 6:** frontend completion update.
- **Later days:** layering, tests, adapters, monitoring, cloud deployment, and infrastructure as introduced by the 16-day plan.

## 16. Open Questions for Client

- Will the system use real PHI, or only fictional/demo data for now?
- What is the exact MRN length? The hard requirement says 6 digits, while the sample shows `00012345`.
- Who is allowed to override duplicate warnings?
- Should generated care plans be editable after generation?
- What file format should pharma reporting exports use?
- Should PDF input be supported in the MVP, or deferred until later?
