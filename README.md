# Care Plan Generator

Small synchronous MVP for generating pharmacist-reviewed care plan drafts.

## What it does

1. A user fills out one web form.
2. The frontend sends the form to the FastAPI backend.
3. The backend calls OpenAI synchronously.
4. The backend stores the submitted request and generated care plan in memory.
5. The frontend displays the generated care plan.

Because storage is in memory only, generated records disappear when the backend restarts.

## Run with Docker Compose

1. Create your env file:

```bash
cp .env.example .env
```

2. Add your real `OPENAI_API_KEY` to `.env`.

3. Start the app:

```bash
docker compose up --build
```

4. Open:

- Frontend: http://localhost:3000
- Backend records: http://localhost:8000/care-plans

## Run locally without Docker

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

Then open http://localhost:3000.

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

## Dependencies

Backend:
- fastapi
- uvicorn
- openai
- python-dotenv
- pydantic

Frontend:
- next
- react
- react-dom
- typescript
