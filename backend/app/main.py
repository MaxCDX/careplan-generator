import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.care_plans.routes import router as care_plans_router
from app.database import init_db
from app.orders.routes import router as orders_router

load_dotenv()
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# The browser app runs on port 3000 during local development and calls this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """Initialize local Day 3 database tables when the FastAPI app starts."""
    # Day 3 learning shortcut. In production, use Alembic migrations instead of
    # creating tables automatically at application startup.
    init_db()


# Keep main.py focused on application wiring; domain endpoints live in routers.
app.include_router(orders_router)
app.include_router(care_plans_router)
